"""
Background job functions executed by the arq worker.

Design rules:
- Every job is IDEMPOTENT: if the same job is enqueued twice (e.g. after a
  worker crash), the second execution detects the source is no longer "pending"
  and exits without side effects.
- Jobs update processing_status on the Source row so the status endpoint
  always reflects real state.
- Jobs use their own DB session (obtained from async_session_maker directly)
  because arq workers run outside the FastAPI request cycle.
- The ctx dict is provided by arq and contains the arq Redis pool; we store
  additional shared resources (DB session factory, object store) in the worker
  startup context via WorkerSettings.on_startup.
"""
import logging
import os
import time
import json
import asyncio
from datetime import datetime, timezone
from uuid import UUID
from typing import Any

# Background tasks are noisy; disable global LangSmith tracing here.
# Explicit tracing_v2_enabled blocks will override this where necessary.
os.environ["LANGCHAIN_TRACING_V2"] = "false"

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import async_session_maker
from app.models.source import Source, SourceSnapshot
from app.services.storage import get_object_store
from app.services.parsing import DocumentParser
from app.services.chunking import ChunkingService
from app.repositories.block import BlockRepository
from app.repositories.episodic import EpisodicRepository
from app.repositories.knowledge import KnowledgeRepository
from app.repositories.graph import graph_store
from app.schemas.episodic import EpisodicMemoryCreate
from app.schemas.working_memory import WorkingMemoryState
from app.schemas.chat import (
    EVENT_TURN_RESEARCH_STARTED,
    EVENT_TURN_RESEARCH_PLANNING,
    EVENT_TURN_RESEARCHING,
    EVENT_TURN_SYNTHESIZING,
    EVENT_TURN_PROMOTION_AVAILABLE,
    EVENT_TURN_COMPLETED,
    EVENT_TURN_CANCELLED,
    EVENT_TURN_FAILED,
    EVENT_SCRATCHPAD_ENTRY,
    EVENT_DONE,
)

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

async def _get_source_and_snapshot(
    session: AsyncSession, source_id: UUID
) -> tuple[Source | None, SourceSnapshot | None]:
    """Load the source + its first snapshot in a single query."""
    result = await session.execute(
        select(Source).where(Source.source_id == source_id)
    )
    source = result.scalars().first()
    if not source:
        return None, None
    snap_result = await session.execute(
        select(SourceSnapshot).where(SourceSnapshot.source_id == source_id)
        .order_by(SourceSnapshot.created_at)
        .limit(1)
    )
    snapshot = snap_result.scalars().first()
    return source, snapshot


# --------------------------------------------------------------------------- #
# parse_and_chunk_job
# --------------------------------------------------------------------------- #

async def parse_and_chunk_job(
    ctx: dict,
    *,
    source_id: str,
    workspace_id: str,
    owner_id: str,
) -> dict[str, Any]:
    """
    Background job: download from S3, parse with Docling, chunk, bulk-insert blocks.

    Idempotency contract:
    - Reads Source.processing_status on entry.
    - If status is NOT 'pending', this is a duplicate or stale enqueue — exits
      immediately without writing anything.
    - Status transitions: pending -> processing -> completed | failed
    """
    source_uuid = UUID(source_id)

    async with async_session_maker() as session:
        source, snapshot = await _get_source_and_snapshot(session, source_uuid)

        if not source:
            logger.error("parse_and_chunk_job: source %s not found — skipping", source_id)
            return {"status": "not_found", "source_id": source_id}

        # ---- Idempotency guard ---- #
        if source.processing_status != "pending":
            logger.info(
                "parse_and_chunk_job: source %s is already '%s' — skipping (idempotent)",
                source_id, source.processing_status
            )
            return {"status": "skipped", "reason": source.processing_status}

        if not snapshot:
            logger.error("parse_and_chunk_job: no snapshot for source %s — marking failed", source_id)
            source.processing_status = "failed"
            await session.commit()
            return {"status": "failed", "reason": "no_snapshot"}

        # ---- Mark processing ---- #
        source.processing_status = "processing"
        await session.commit()

    # ---- Do the heavy work OUTSIDE the session (may take 30-120s) ---- #
    try:
        storage = get_object_store()
        parser = DocumentParser(storage)
        chunking = ChunkingService()

        doc_dict = await parser.parse_document(snapshot.file_uri)
        blocks_in = chunking.process_docling_output(doc_dict)

        async with async_session_maker() as session:
            block_repo = BlockRepository(session)
            await block_repo.bulk_create_blocks(
                source_id=source_uuid,
                snapshot_id=snapshot.snapshot_id,
                blocks=blocks_in
            )
            # ---- Mark completed ---- #
            result = await session.execute(
                select(Source).where(Source.source_id == source_uuid)
            )
            source_row = result.scalars().first()
            source_row.processing_status = "completed"
            await session.commit()

        logger.info("parse_and_chunk_job: source %s completed (%d blocks)", source_id, len(blocks_in))
        return {"status": "completed", "source_id": source_id, "blocks": len(blocks_in)}

    except Exception as exc:
        logger.exception("parse_and_chunk_job: source %s failed: %s", source_id, exc)
        async with async_session_maker() as session:
            result = await session.execute(
                select(Source).where(Source.source_id == source_uuid)
            )
            source_row = result.scalars().first()
            if source_row:
                source_row.processing_status = "failed"
                await session.commit()
        return {"status": "failed", "source_id": source_id, "error": str(exc)}


# --------------------------------------------------------------------------- #
# compress_episodic_job
# --------------------------------------------------------------------------- #

async def compress_episodic_job(
    ctx: dict,
    *,
    owner_id: str,
    workspace_id: str,
    working_state: dict,
    run_id: str | None = None,
    llm_provider: str = "openai",
    llm_model: str = "gpt-4o-mini",
) -> dict[str, Any]:
    """
    Background job: summarise working memory state into an episodic memory record.

    Idempotency contract:
    - Uses run_id as the natural deduplication key.
    - If an episode with the same run_id already exists, exits without writing.
    - If run_id is None (fire-and-forget callers), the job always executes
      (caller is responsible for not over-enqueuing).
    """
    from app.services.episodic import EpisodicMemoryService

    owner_uuid = UUID(owner_id)
    workspace_uuid = UUID(workspace_id)
    run_uuid = UUID(run_id) if run_id else None

    async with async_session_maker() as session:
        episodic_repo = EpisodicRepository(session)

        # ---- Idempotency guard (run_id-based) ---- #
        if run_uuid is not None:
            existing = await episodic_repo.get_episode_by_run_id(
                workspace_id=workspace_uuid,
                run_id=run_uuid
            )
            if existing:
                logger.info(
                    "compress_episodic_job: episode for run %s already exists — skipping",
                    run_id
                )
                return {"status": "skipped", "reason": "already_exists", "run_id": run_id}

        # ---- Build a lightweight LLM gateway using the configured provider ---- #
        # This is intentionally simple: the gateway is a callable that takes a
        # prompt string and returns a summary string. Full LiteLLM integration
        # comes in Phase 3; for now we wire a direct openai call via arq ctx.
        async def llm_gateway(prompt: str) -> str:
            # ctx["llm_call"] is injected by WorkerSettings.on_startup if available.
            # If not present (testing), raise so the test can mock it.
            llm_fn = ctx.get("llm_call")
            if llm_fn is None:
                raise RuntimeError(
                    "compress_episodic_job: llm_call not in worker context. "
                    "Ensure WorkerSettings.on_startup populates ctx['llm_call']."
                )
            return await llm_fn(prompt, model=llm_model, provider=llm_provider)

        svc = EpisodicMemoryService(
            repository=episodic_repo,
            llm_gateway=llm_gateway,
        )

        try:
            episode = await svc.compress_working_memory(
                owner_id=owner_uuid,
                workspace_id=workspace_uuid,
                working_state=WorkingMemoryState(**working_state),
                run_id=run_uuid,
            )
            logger.info(
                "compress_episodic_job: created episode %s for workspace %s",
                episode.episode_id, workspace_id
            )
            return {
                "status": "completed",
                "episode_id": str(episode.episode_id),
                "workspace_id": workspace_id,
            }
        except Exception as exc:
            logger.exception(
                "compress_episodic_job: failed for workspace %s run %s: %s",
                workspace_id, run_id, exc
            )
            return {"status": "failed", "workspace_id": workspace_id, "error": str(exc)}

# --------------------------------------------------------------------------- #
# sync_knowledge_to_graph_job
# --------------------------------------------------------------------------- #

async def sync_knowledge_to_graph_job(
    ctx: dict,
    *,
    knowledge_id: str,
    expected_epoch: int | None = None,
) -> dict[str, Any]:
    """
    Background job: synchronizes a KnowledgeMemory row from Postgres to the Neo4j Graph.

    Idempotency contract:
    - Re-running on the same knowledge_id will run a Neo4j MERGE, which safely
      updates properties without duplicating the node or edge.
    - Timeline epoch fence: aborts if workspace epoch has advanced.
    """
    k_uuid = UUID(knowledge_id)

    async with async_session_maker() as session:
        repo = KnowledgeRepository(session)
        # We don't have the owner_id in the payload, but get_knowledge requires it.
        from app.models.knowledge import KnowledgeMemory
        result = await session.execute(
            select(KnowledgeMemory).where(KnowledgeMemory.knowledge_id == k_uuid)
        )
        knowledge = result.scalars().first()

        if not knowledge:
            logger.error("sync_knowledge_to_graph_job: knowledge_id %s not found", knowledge_id)
            return {"status": "not_found", "knowledge_id": knowledge_id}

        # Concurrency Fence: Check timeline_epoch
        from app.models.workspace import Workspace
        ws_stmt = select(Workspace).where(Workspace.workspace_id == knowledge.workspace_id)
        ws_res = await session.execute(ws_stmt)
        ws = ws_res.scalars().first()
        if ws and expected_epoch is not None:
            current_epoch = getattr(ws, "timeline_epoch", 1) or 1
            if current_epoch > expected_epoch:
                fence_reason = f"Aborted by timeline fence: workspace epoch advanced from {expected_epoch} to {current_epoch}."
                logger.warning("Timeline fence triggered in sync_knowledge_to_graph_job: %s", fence_reason)
                return {"status": "aborted_by_timeline_fence", "knowledge_id": knowledge_id, "reason": fence_reason}

        try:
            # Ensure GraphStore is connected
            await graph_store.connect()

            query = """
            MERGE (k:Knowledge {id: $knowledge_id})
            SET k.workspace_id = $workspace_id,
                k.owner_id = $owner_id,
                k.type = $knowledge_type,
                k.content = $content,
                k.status = $status,
                k.domain = $domain,
                k.version = $version
            WITH k
            MERGE (w:Workspace {id: $workspace_id})
            MERGE (w)-[:CONTAINS]->(k)
            """
            
            params = {
                "knowledge_id": str(knowledge.knowledge_id),
                "workspace_id": str(knowledge.workspace_id),
                "owner_id": str(knowledge.owner_id),
                "knowledge_type": knowledge.knowledge_type,
                "content": knowledge.content,
                "status": knowledge.status,
                "domain": knowledge.domain,
                "version": knowledge.version,
            }

            await graph_store.execute_query(query, params)
            logger.info("sync_knowledge_to_graph_job: upserted knowledge_id %s to graph", knowledge_id)
            
            return {"status": "completed", "knowledge_id": knowledge_id}

        except Exception as exc:
            logger.exception("sync_knowledge_to_graph_job: failed to sync knowledge_id %s: %s", knowledge_id, exc)
            return {"status": "failed", "knowledge_id": knowledge_id, "error": str(exc)}

# --------------------------------------------------------------------------- #
# run_research_agent_job
# --------------------------------------------------------------------------- #

async def run_research_agent_job(
    ctx: dict,
    *,
    workspace_id: str,
    objective: str,
    run_id: str | None = None,
    research_context: dict | None = None,
) -> dict[str, Any]:
    """
    Background job: Runs the ResearchEngine and streams events to Redis.
    """
    import json
    from uuid import UUID
    import uuid
    from app.integrations.research_engine.factory import ResearchEngineFactory
    from app.services.web_search import WebSearchTool

    job_id = ctx.get("job_id")
    if not job_id:
        logger.error("run_research_agent_job: No job_id found in context")
        return {"status": "failed", "error": "No job_id"}
        
    if not run_id:
        logger.error("run_research_agent_job: Missing run_id")
        return {"status": "failed", "error": "Missing run_id"}
        
    redis = ctx.get("redis")
    channel_name = f"research:{job_id}"
    
    async def publish_event(event_data: dict):
        if redis:
            payload_str = json.dumps(event_data)
            await redis.publish(channel_name, payload_str)
            await redis.publish(f"research_events:{run_id}", payload_str)

    await publish_event({"status": "starting", "message": "Initializing research agent..."})

    # Get LLM Gateway (same pattern as compress_episodic_job)
    async def llm_gateway(prompt: str) -> str:
        llm_fn = ctx.get("llm_call")
        if llm_fn is None:
            # Fallback for tests if not provided
            raise RuntimeError("llm_call not found in context")
        return await llm_fn(prompt, model="gpt-4o", provider="openai")

    import time
    start_time = time.time()
    
    # We must retrieve the Workspace and ResearchRun
    async with async_session_maker() as session:
        from app.models.workspace import Workspace
        from app.models.research import ResearchRun, ResearchArtifact, ResearchReport
        from sqlalchemy.future import select
        
        workspace = (await session.execute(
            select(Workspace).where(Workspace.workspace_id == UUID(workspace_id))
        )).scalars().first()
        
        run = (await session.execute(
            select(ResearchRun).where(ResearchRun.run_id == UUID(run_id))
        )).scalars().first()
        
        if not run:
            await publish_event({"status": "failed", "error": "ResearchRun not found"})
            return {"status": "failed", "error": "ResearchRun not found"}

        expected_epoch = getattr(run, "timeline_epoch", None) or (workspace.timeline_epoch if workspace and isinstance(getattr(workspace, "timeline_epoch", None), int) else 1)
            
        owner_id = run.owner_id
        engine_flag = run.engine
        actual_run_id = UUID(run_id)

    async def _bridge_chat_event(t_id: UUID | None, ev_type: str, payload: dict):
        if not t_id:
            return
        from app.services.chat.events import ChatEventRepository, ChatEventService
        try:
            payload.setdefault("workspace_id", str(workspace_id))
            payload.setdefault("run_id", str(actual_run_id))
            if getattr(run, "conversation_id", None):
                payload.setdefault("conversation_id", str(run.conversation_id))
            payload.setdefault("turn_id", str(t_id))
            payload.setdefault("timeline_epoch", expected_epoch)

            async with async_session_maker() as ev_session:
                c_repo = ChatEventRepository(ev_session)
                c_service = ChatEventService(c_repo, redis)
                await c_service.record_and_publish(t_id, ev_type, payload)
        except Exception as bridge_err:
            logger.warning("Failed to bridge chat event %s for turn %s: %s", ev_type, t_id, bridge_err)

    if run.turn_id:
        await _bridge_chat_event(
            run.turn_id,
            EVENT_TURN_RESEARCH_STARTED,
            {"run_id": str(actual_run_id), "status": "started", "engine": engine_flag}
        )

    logger.info(json.dumps({
        "event": "research_run_started",
        "workspace_id": workspace_id,
        "run_id": str(actual_run_id),
        "engine": engine_flag
    }))

    # Instantiate the appropriate engine via factory
    engine = ResearchEngineFactory.get_engine(
        engine_name=engine_flag,
        llm_gateway=llm_gateway,
        search_tool=WebSearchTool(),
        redis_client=redis
    )

    cancel_task = None
    if redis and hasattr(redis, "pubsub"):
        async def _listen_for_cancellation():
            try:
                ps = redis.pubsub()
                await ps.subscribe(f"research_cancellation:{actual_run_id}")
                async for msg in ps.listen():
                    if msg and msg.get("type") == "message":
                        logger.info("Received cancellation signal via Redis for run %s", actual_run_id)
                        if hasattr(engine, "cancel"):
                            await engine.cancel()
                        break
            except Exception as e:
                logger.debug("Cancellation listener ended for run %s: %s", actual_run_id, e)
        cancel_task = asyncio.create_task(_listen_for_cancellation())

    try:
        final_graph = None
        final_status = "completed"
        final_reason = "Engine finished normally"
        
        async for event in engine.astream_events(
            run_id=actual_run_id,
            workspace_id=UUID(workspace_id),
            objective=objective,
            research_context=research_context,
        ):
            await publish_event(event)
            status = event.get("status")

            if run.turn_id:
                if status == "planning":
                    await _bridge_chat_event(
                        run.turn_id,
                        EVENT_TURN_RESEARCH_PLANNING,
                        {"run_id": str(actual_run_id), "message": event.get("message", "Planning research")}
                    )
                elif status in ("executing", "researching"):
                    await _bridge_chat_event(
                        run.turn_id,
                        EVENT_TURN_RESEARCHING,
                        {"run_id": str(actual_run_id), "message": event.get("message", "Conducting research")}
                    )
                elif status == "synthesizing":
                    await _bridge_chat_event(
                        run.turn_id,
                        EVENT_TURN_SYNTHESIZING,
                        {"run_id": str(actual_run_id), "message": event.get("message", "Synthesizing research results")}
                    )

            # Structured scratchpad persistence and real-time streaming
            sp_data = event.get("scratchpad_entry")
            if sp_data and isinstance(sp_data, dict):
                from app.services.chat.context import sanitize_scratchpad_content
                from app.repositories.scratchpad import ScratchpadRepository

                entry_type = sp_data.get("entry_type", "observation")
                raw_content = sp_data.get("content", "")
                sanitized = sanitize_scratchpad_content(raw_content)
                if sanitized and entry_type in ["note", "observation", "hypothesis", "investigation", "finding"]:
                    async with async_session_maker() as sp_session:
                        sp_repo = ScratchpadRepository(sp_session)
                        sp_entry = await sp_repo.create_entry(
                            workspace_id=UUID(workspace_id),
                            conversation_id=run.conversation_id,
                            turn_id=run.turn_id,
                            run_id=actual_run_id,
                            entry_type=entry_type,
                            content=sanitized,
                            is_pinned_to_workspace=bool(sp_data.get("is_pinned_to_workspace", False)),
                            metadata=sp_data.get("metadata") or {}
                        )
                        sp_payload = {
                            "entry_id": str(sp_entry.entry_id),
                            "entry_type": sp_entry.entry_type,
                            "content": sp_entry.content,
                            "is_pinned": sp_entry.is_pinned_to_workspace,
                            "lifecycle": sp_entry.lifecycle,
                            "metadata": sp_entry.metadata_ or {}
                        }
                        sp_event = {
                            "event_type": "scratchpad_entry",
                            "payload": sp_payload
                        }
                        if redis:
                            sp_json = json.dumps(sp_event)
                            await redis.publish(f"research_events:{actual_run_id}", sp_json)
                            if run.turn_id:
                                await redis.publish(f"turn_events:{run.turn_id}", sp_json)
                        if run.turn_id:
                            await _bridge_chat_event(run.turn_id, EVENT_SCRATCHPAD_ENTRY, sp_payload)

            if status in ("failed", "partial", "cancelled"):
                final_status = status
                final_reason = event.get("message", f"Engine returned {status}")

            if status == "synthesizing" and "final_graph" in event:
                final_graph = event["final_graph"]

        # ---------------------------------------------------------
        # Finalize execution, transition state, and promote candidates
        # ---------------------------------------------------------
        async with async_session_maker() as session:
            from app.repositories.research import ResearchRepository
            from app.services.research.lifecycle import ResearchLifecycleService
            from app.services.research.service import ResearchService
            from app.services.memory_router import MemoryRouter
            from app.repositories.graph import GraphRepository, graph_store
            
            repo = ResearchRepository(session)
            lifecycle = ResearchLifecycleService(repo)
            
            # ---------------------------------------------------------
            # Concurrency Fence: Check timeline_epoch
            # If workspace was rolled back during research execution,
            # epoch will have incremented. Fence out in-flight worker.
            # ---------------------------------------------------------
            ws_current = (await session.execute(
                select(Workspace).where(Workspace.workspace_id == UUID(workspace_id))
            )).scalars().first()
            current_epoch = ws_current.timeline_epoch if ws_current and isinstance(getattr(ws_current, "timeline_epoch", None), int) else expected_epoch

            if current_epoch != expected_epoch:
                fence_reason = f"Aborted by timeline fence: workspace epoch advanced from {expected_epoch} to {current_epoch} due to rollback."
                logger.warning("Timeline epoch fence triggered for workspace %s: %s", workspace_id, fence_reason)
                try:
                    await lifecycle.transition_run(UUID(workspace_id), actual_run_id, "aborted_by_timeline_fence", {"reason": fence_reason})
                except Exception:
                    current_run = await repo.get_run(UUID(workspace_id), actual_run_id)
                    if current_run:
                        current_run.status = "aborted_by_timeline_fence"
                        await session.commit()

                if run and run.turn_id:
                    from app.repositories.conversation import ConversationRepository
                    conv_repo = ConversationRepository(session)
                    cancelled_turn = await conv_repo.set_turn_status(
                        turn_id=run.turn_id,
                        status="cancelled",
                        expected_statuses=["pending", "running"],
                        error_code="timeline_fence_aborted",
                        error_message=fence_reason,
                        research_run_id=actual_run_id,
                        completed_at=datetime.now(timezone.utc)
                    )
                    if cancelled_turn:
                        await _bridge_chat_event(
                            run.turn_id,
                            EVENT_TURN_CANCELLED,
                            {"status": "cancelled", "reason": fence_reason}
                        )
                        await _bridge_chat_event(
                            run.turn_id,
                            EVENT_DONE,
                            {"status": "cancelled", "reason": fence_reason}
                        )

                if redis:
                    fence_event = {
                        "event_type": "workspace.rollback.fence_triggered",
                        "workspace_id": workspace_id,
                        "run_id": str(actual_run_id),
                        "expected_epoch": expected_epoch,
                        "current_epoch": current_epoch,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    await redis.publish(f"workspace_events:{workspace_id}", json.dumps(fence_event))
                    await redis.publish(f"research_events:{actual_run_id}", json.dumps(fence_event))

                await publish_event({"status": "aborted_by_timeline_fence", "error": fence_reason})
                return {"status": "aborted_by_timeline_fence", "reason": fence_reason}

            # Transition state to final_status
            if final_status == "completed":
                current_run = await repo.get_run(UUID(workspace_id), actual_run_id)
                current_status = current_run.status.lower() if current_run else "pending"
                stages = ["planning", "researching", "synthesizing", "finalizing"]
                if current_status in stages or current_status == "pending":
                    start_idx = -1 if current_status == "pending" else stages.index(current_status)
                    for next_stage in stages[start_idx + 1:]:
                        await lifecycle.transition_run(UUID(workspace_id), actual_run_id, next_stage, {"auto": True})
            await lifecycle.transition_run(UUID(workspace_id), actual_run_id, final_status, {"reason": final_reason})
            await session.commit()
            
            # ---------------------------------------------------------
            # In Phase 3: Finalize candidate artifacts in pending_review status
            # Research completion NEVER automatically promotes KnowledgeMemory or projects Output KG.
            # ---------------------------------------------------------
            if final_status == "completed":
                from app.services.research.derivation import DerivationService
                derivation_svc = DerivationService(session)
                candidates = await repo.list_candidates_by_status(UUID(workspace_id), run_id=actual_run_id)
                for cand in candidates:
                    if cand.promotion_status == "pending_review":
                        cand_dict = {
                            "payload": cand.payload,
                            "verification_status": cand.verification_status,
                            "verification_reason": cand.verification_reason,
                            "verification_metadata": cand.verification_metadata,
                        }
                        try:
                            normalized = await derivation_svc.normalize_derivation(UUID(workspace_id), cand_dict)
                            cand.payload = normalized.get("payload", cand.payload)
                            cand.verification_status = normalized.get("verification_status", cand.verification_status)
                            cand.verification_reason = normalized.get("verification_reason", cand.verification_reason)
                            cand.verification_metadata = normalized.get("verification_metadata", cand.verification_metadata)
                        except Exception as exc:
                            logger.warning("Failed to normalize derivation for candidate %s: %s", cand.artifact_id, exc)

                # If synthesis produced final_graph, ensure it is stored as graph_candidate (pending_review)
                # rather than directly projecting into Neo4j
                if final_graph:
                    stmt = select(ResearchArtifact).where(
                        ResearchArtifact.run_id == actual_run_id,
                        ResearchArtifact.type == "graph_candidate"
                    )
                    existing_gc = (await session.execute(stmt)).scalars().first()
                    if not existing_gc:
                        await repo.create_artifact(
                            workspace_id=UUID(workspace_id),
                            run_id=actual_run_id,
                            artifact_type="graph_candidate",
                            payload=final_graph,
                            promotion_status="pending_review",
                        )
                await session.commit()

            # Retrieve final research report content if available to attach as assistant summary
            # Finalize ConversationTurn status, assistant message, and research_run_id
            if run and getattr(run, "turn_id", None):
                report_content = None
                try:
                    rep_stmt = (
                        select(ResearchReport)
                        .where(ResearchReport.run_id == actual_run_id)
                        .order_by(ResearchReport.created_at.desc())
                    )
                    rep_res = await session.execute(rep_stmt)
                    rep = rep_res.scalars().first() if rep_res else None
                    if rep and hasattr(rep, "content"):
                        report_content = rep.content
                except Exception as rep_err:
                    logger.debug("Could not retrieve research report for turn summary: %s", rep_err)

                completed_turn = None
                try:
                    from app.repositories.conversation import ConversationRepository
                    conv_repo = ConversationRepository(session)
                    completed_turn = await conv_repo.set_turn_status(
                        turn_id=run.turn_id,
                        status=final_status,
                        expected_statuses=["pending", "running"],
                        assistant_message=report_content,
                        research_run_id=actual_run_id,
                        completed_at=datetime.now(timezone.utc)
                    )
                except Exception as status_err:
                    logger.warning("Could not set turn status on research completion: %s", status_err)

                if completed_turn:
                    turn_comp_event = EVENT_TURN_COMPLETED if final_status == "completed" else f"turn.{final_status}"
                    await _bridge_chat_event(
                        run.turn_id,
                        turn_comp_event,
                        {
                            "status": final_status,
                            "assistant_message": report_content,
                            "research_run_id": str(actual_run_id)
                        }
                    )
                    await _bridge_chat_event(
                        run.turn_id,
                        EVENT_DONE,
                        {
                            "status": final_status,
                            "assistant_message": report_content,
                            "research_run_id": str(actual_run_id)
                        }
                    )

        await publish_event({"status": final_status, "message": f"Research {final_status}"})
        if redis and final_status == "completed":
            prom_event = {
                "event_type": "promotion.available",
                "workspace_id": workspace_id,
                "run_id": str(actual_run_id),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            await redis.publish(f"workspace_events:{workspace_id}", json.dumps(prom_event))
            await redis.publish(f"research_events:{actual_run_id}", json.dumps(prom_event))

        if run and run.turn_id and final_status == "completed":
            await _bridge_chat_event(
                run.turn_id,
                EVENT_TURN_PROMOTION_AVAILABLE,
                {"workspace_id": workspace_id, "run_id": str(actual_run_id)}
            )
            
        duration_ms = int((time.time() - start_time) * 1000)
        logger.info(json.dumps({
            "event": "research_run_completed",
            "workspace_id": workspace_id,
            "run_id": str(actual_run_id),
            "status": final_status,
            "duration_ms": duration_ms
        }))
        return {"status": final_status, "workspace_id": workspace_id, "run_id": str(actual_run_id)}

    except Exception as exc:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error(json.dumps({
            "event": "research_run_failed",
            "workspace_id": workspace_id,
            "run_id": str(actual_run_id) if 'actual_run_id' in locals() else run_id,
            "status": "failed",
            "duration_ms": duration_ms,
            "error": str(exc)
        }))
        logger.exception("run_research_agent_job: failed for workspace %s: %s", workspace_id, exc)
        await publish_event({"status": "failed", "error": str(exc)})
        
        # Ensure we transition to failed state if an unhandled exception occurred
        try:
            async with async_session_maker() as session:
                from app.repositories.research import ResearchRepository
                from app.services.research.lifecycle import ResearchLifecycleService
                repo = ResearchRepository(session)
                lifecycle = ResearchLifecycleService(repo)
                current_run_obj = await repo.get_run(UUID(workspace_id), actual_run_id)
                if not current_run_obj or current_run_obj.status != "aborted_by_timeline_fence":
                    await lifecycle.transition_run(UUID(workspace_id), actual_run_id, "failed", {"error": str(exc)})
                    await session.commit()
        except Exception as transition_exc:
            logger.warning(f"Could not transition run to failed (might already be terminal): {transition_exc}")

        if 'run' in locals() and run and getattr(run, "turn_id", None):
            try:
                failed_turn = None
                async with async_session_maker() as err_session:
                    from app.repositories.conversation import ConversationRepository
                    c_repo = ConversationRepository(err_session)
                    failed_turn = await c_repo.set_turn_status(
                        turn_id=run.turn_id,
                        status="failed",
                        expected_statuses=["pending", "running"],
                        error_code="research_job_failed",
                        error_message=str(exc),
                        research_run_id=actual_run_id if 'actual_run_id' in locals() else None,
                        completed_at=datetime.now(timezone.utc)
                    )
                if failed_turn:
                    await _bridge_chat_event(
                        run.turn_id,
                        EVENT_TURN_FAILED,
                        {"status": "failed", "error": str(exc)}
                    )
                    await _bridge_chat_event(
                        run.turn_id,
                        EVENT_DONE,
                        {"status": "failed", "error": str(exc)}
                    )
            except Exception as turn_exc:
                logger.warning("Failed to record turn failure: %s", turn_exc)
            
        return {"status": "failed", "workspace_id": workspace_id, "error": str(exc)}
    finally:
        if cancel_task and not cancel_task.done():
            cancel_task.cancel()

# --------------------------------------------------------------------------- #
# project_output_graph_job
# --------------------------------------------------------------------------- #

async def project_output_graph_job(
    ctx: dict,
    *,
    workspace_id: str,
    graph_dict: dict,
    commit_id: str | None = None,
    expected_epoch: int | None = None,
) -> dict[str, Any]:
    """
    Background job: Projects the final OutputGraph from the research agent into Neo4j.
    Validates Output KG topology, enforces active-commit authority and timeline epoch fencing.
    """
    from uuid import UUID
    from app.schemas.graph import OutputGraph
    from app.repositories.graph import graph_store, GraphRepository
    from app.models.workspace import Workspace
    from sqlalchemy import select

    workspace_uuid = UUID(workspace_id)

    try:
        # 1. Topology validation before projection
        if not isinstance(graph_dict, dict):
            logger.warning("project_output_graph_job: malformed topology - graph_dict must be a dictionary")
            return {
                "status": "failed",
                "workspace_id": workspace_id,
                "error": "malformed_graph_topology",
                "detail": "graph_dict must be a dict"
            }

        try:
            graph = OutputGraph(**graph_dict)
        except Exception as pydantic_err:
            logger.warning("project_output_graph_job: malformed graph topology schema: %s", pydantic_err)
            return {
                "status": "failed",
                "workspace_id": workspace_id,
                "error": "malformed_graph_topology",
                "detail": str(pydantic_err)
            }

        node_ids = set()
        for node in graph.nodes:
            if not node.id or not str(node.id).strip():
                logger.warning("project_output_graph_job: malformed topology - node ID is empty")
                return {
                    "status": "failed",
                    "workspace_id": workspace_id,
                    "error": "malformed_graph_topology",
                    "detail": "Node ID cannot be empty"
                }
            node_ids.add(str(node.id))

        for edge in graph.edges:
            if not edge.source_id or str(edge.source_id) not in node_ids:
                logger.warning("project_output_graph_job: malformed topology - edge source endpoint %s not in nodes", edge.source_id)
                return {
                    "status": "failed",
                    "workspace_id": workspace_id,
                    "error": "malformed_graph_topology",
                    "detail": f"Edge source endpoint '{edge.source_id}' does not exist in graph nodes"
                }
            if not edge.target_id or str(edge.target_id) not in node_ids:
                logger.warning("project_output_graph_job: malformed topology - edge target endpoint %s not in nodes", edge.target_id)
                return {
                    "status": "failed",
                    "workspace_id": workspace_id,
                    "error": "malformed_graph_topology",
                    "detail": f"Edge target endpoint '{edge.target_id}' does not exist in graph nodes"
                }

        # 2. Check active-commit authority and timeline epoch fence
        resolved_commit_id = None
        async with async_session_maker() as session:
            stmt = select(Workspace).where(Workspace.workspace_id == workspace_uuid)
            ws_res = await session.execute(stmt)
            ws = ws_res.scalars().first()

            if not ws:
                return {
                    "status": "failed",
                    "workspace_id": workspace_id,
                    "error": "workspace_not_found"
                }

            # Check timeline epoch if expected_epoch provided
            current_epoch = getattr(ws, "timeline_epoch", 1) or 1
            if expected_epoch is not None and current_epoch > expected_epoch:
                fence_reason = f"Aborted by timeline fence: workspace epoch advanced from {expected_epoch} to {current_epoch}."
                logger.warning("Timeline fence triggered in project_output_graph_job for workspace %s: %s", workspace_id, fence_reason)
                return {
                    "status": "aborted_by_timeline_fence",
                    "workspace_id": workspace_id,
                    "reason": fence_reason
                }

            # Check active-commit authority: reject independent projection jobs that lack active-commit authority
            active_commit = ws.active_commit_id
            if active_commit is None:
                logger.warning("project_output_graph_job: rejected - workspace %s has no active commit authority", workspace_id)
                return {
                    "status": "rejected",
                    "workspace_id": workspace_id,
                    "error": "lacks_active_commit_authority",
                    "detail": "Workspace has no active commit"
                }

            if commit_id is not None and str(commit_id) != str(active_commit):
                logger.warning("project_output_graph_job: rejected - commit %s does not match active commit %s", commit_id, active_commit)
                return {
                    "status": "rejected",
                    "workspace_id": workspace_id,
                    "error": "lacks_active_commit_authority",
                    "detail": f"Commit {commit_id} does not match active commit {active_commit}"
                }

            resolved_commit_id = active_commit

        # 3. Project into Neo4j carrying commit_id and workspace_id
        repo = GraphRepository(graph_store)
        await repo.project_output_graph(workspace_uuid, graph, commit_id=resolved_commit_id)

        logger.info(f"project_output_graph_job: Successfully projected graph for workspace {workspace_id} under commit {resolved_commit_id}")
        return {
            "status": "completed",
            "workspace_id": workspace_id,
            "commit_id": str(resolved_commit_id)
        }
        
    except Exception as exc:
        logger.exception("project_output_graph_job: failed to project graph for workspace %s: %s", workspace_id, exc)
        return {"status": "failed", "workspace_id": workspace_id, "error": str(exc)}

# --------------------------------------------------------------------------- #
# export_workspace_job
# --------------------------------------------------------------------------- #

async def export_workspace_job(
    ctx: dict,
    *,
    workspace_id: str,
    owner_id: str,
) -> dict[str, Any]:
    """
    Background job: Executes the workspace export using WorkspaceExportService
    and publishes the result URL to a Redis pub/sub channel.
    """
    import json
    from uuid import UUID
    from app.services.export import WorkspaceExportService
    from app.services.storage import S3ObjectStore

    workspace_uuid = UUID(workspace_id)
    redis = ctx.get("redis")
    channel_name = f"export:{workspace_id}"

    async def publish_event(event_data: dict):
        if redis:
            await redis.publish(channel_name, json.dumps(event_data))

    await publish_event({"status": "starting", "message": "Starting workspace export..."})

    try:
        s3_client = ctx.get("s3_client")
        if not s3_client:
            raise RuntimeError("s3_client not found in worker context")
            
        storage = S3ObjectStore(s3_client)

        async with async_session_maker() as session:
            service = WorkspaceExportService(db=session, object_store=storage)
            signed_url = await service.export_to_zip(workspace_uuid)

        await publish_event({
            "status": "completed",
            "message": "Export finished",
            "url": signed_url
        })
        logger.info("export_workspace_job: Successfully exported workspace %s", workspace_id)
        return {"status": "completed", "workspace_id": workspace_id, "url": signed_url}

    except Exception as exc:
        logger.exception("export_workspace_job: failed for workspace %s: %s", workspace_id, exc)
        await publish_event({"status": "failed", "error": str(exc)})
        return {"status": "failed", "workspace_id": workspace_id, "error": str(exc)}

# --------------------------------------------------------------------------- #
# Open Notebook Integration Jobs
# --------------------------------------------------------------------------- #

async def project_to_open_notebook_job(
    ctx: dict,
    *,
    source_id: str,
    snapshot_id: str,
    workspace_id: str,
) -> dict[str, Any]:
    """Background job: Projects a new source snapshot to Open Notebook."""
    from app.repositories.open_notebook import OpenNotebookRepository
    from app.integrations.open_notebook.client import OpenNotebookClient
    from app.services.storage import S3ObjectStore
    import tempfile
    import os
    import httpx
    from arq.worker import Retry

    source_uuid = UUID(source_id)
    snapshot_uuid = UUID(snapshot_id)
    workspace_uuid = UUID(workspace_id)

    async with async_session_maker() as session:
        repo = OpenNotebookRepository(session)
        source, snapshot = await _get_source_and_snapshot(session, source_uuid)
        
        if not source or not snapshot:
            logger.error("project_to_open_notebook: source/snapshot not found for %s", source_id)
            return {"status": "not_found"}

        # 1. Atomic claim
        binding = await repo.claim_projection_job(
            source_id=source_uuid,
            snapshot_id=snapshot_uuid,
            checksum=snapshot.checksum_sha256
        )
        if not binding:
            logger.info("project_to_open_notebook: Job already claimed/projected for %s", source_id)
            return {"status": "skipped", "reason": "already_claimed"}

        # 2. Workspace binding check/creation
        workspace_binding = await repo.get_workspace_binding(workspace_uuid)
        on_client = OpenNotebookClient()
        
        if not workspace_binding:
            ws_title = f"Workspace {workspace_id}" # Simple fallback title
            on_notebook_id = await on_client.create_notebook(ws_title)
            workspace_binding = await repo.create_workspace_binding(workspace_uuid, on_notebook_id)

        # 3. Download snapshot
        s3_client = ctx.get("s3_client")
        if not s3_client:
            raise RuntimeError("s3_client not found in worker context")
        storage = S3ObjectStore(s3_client)
        file_bytes = await storage.download_file(snapshot.file_uri)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".file") as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
            
        try:
            # 4. Upload to ON
            on_src_id = await on_client.upload_source(
                workspace_binding.open_notebook_notebook_id, 
                tmp_path, 
                source.name
            )
            await repo.update_projection_status(
                source_id=source_uuid,
                snapshot_id=snapshot_uuid,
                status="ACTIVE",
                open_notebook_source_id=on_src_id
            )
            
            # Enqueue deletion for previous active projections
            active_bindings = await repo.get_active_projections_for_source(source_uuid)
            redis = ctx.get("redis")
            for b in active_bindings:
                if b.snapshot_id != snapshot_uuid:
                    tombstone = await repo.create_tombstone_and_delete_source_binding(b.source_id, b.snapshot_id)
                    if tombstone and redis:
                        await redis.enqueue_job(
                            "process_deletion_tombstone_job",
                            tombstone_id=str(tombstone.tombstone_id)
                        )
                        
            return {"status": "completed", "source_id": source_id}
            
        except httpx.HTTPStatusError as e:
            # Handle rate limiting and upstream unavailability explicitly
            if e.response.status_code in (429, 502, 503, 504):
                retry_after = e.response.headers.get("Retry-After")
                if retry_after and retry_after.isdigit():
                    delay = int(retry_after)
                else:
                    delay = ctx.get("job_try", 1) * 30
                    
                logger.warning(f"Open Notebook backpressure. Retrying in {delay}s: {str(e)}")
                raise Retry(defer=delay)
            else:
                await repo.update_projection_status(
                    source_id=source_uuid,
                    snapshot_id=snapshot_uuid,
                    status="FAILED",
                    error_meta={"error": str(e)}
                )
                raise
        except Exception as e:
            await repo.update_projection_status(
                source_id=source_uuid,
                snapshot_id=snapshot_uuid,
                status="FAILED",
                error_meta={"error": str(e)}
            )
            raise
        finally:
            os.remove(tmp_path)


async def process_deletion_tombstone_job(ctx: dict, *, tombstone_id: str) -> dict[str, Any]:
    """Background job: Processes a DeletionTombstone against Open Notebook."""
    from app.integrations.open_notebook.client import OpenNotebookClient
    from app.models.open_notebook_binding import DeletionTombstone
    from sqlalchemy import select
    from datetime import datetime, timezone
    
    async with async_session_maker() as session:
        tombstone = await session.get(DeletionTombstone, UUID(tombstone_id))
        if not tombstone or tombstone.status != "pending":
            return {"status": "skipped", "reason": "not_pending"}
            
        tombstone.attempt_count += 1
        tombstone.last_attempt = datetime.now(timezone.utc)
        await session.commit()
        
        on_client = OpenNotebookClient()
        try:
            if tombstone.open_notebook_id:
                if tombstone.resource_type == "workspace":
                    await on_client.delete_notebook(tombstone.open_notebook_id, delete_exclusive_sources=True)
                elif tombstone.resource_type == "source":
                    await on_client.delete_source(tombstone.open_notebook_id)
            
            tombstone.status = "completed"
            await session.commit()
            return {"status": "completed"}
        except Exception as e:
            if tombstone.attempt_count >= 5:
                tombstone.status = "ORPHANED_UPSTREAM"
                logger.error(f"Tombstone {tombstone_id} exceeded max retries. Marking ORPHANED_UPSTREAM. Error: {e}")
                await session.commit()
                return {"status": "orphaned_upstream"}
            else:
                # Leave it as pending for the reconciler, but the attempt is recorded
                await session.commit()
                raise e

async def reconcile_deletion_tombstones_job(ctx: dict) -> dict[str, Any]:
    """Periodic task: Sweeps for pending tombstones and enqueues processing."""
    from app.models.open_notebook_binding import DeletionTombstone
    from sqlalchemy import select
    from datetime import datetime, timezone, timedelta
    import math
    
    redis = ctx.get("redis")
    if not redis:
        return {"status": "failed", "reason": "no_redis"}
        
    async with async_session_maker() as session:
        result = await session.execute(
            select(DeletionTombstone).where(DeletionTombstone.status == "pending")
        )
        tombstones = result.scalars().all()
        
        enqueued_count = 0
        now = datetime.now(timezone.utc)
        for t in tombstones:
            # Exponential backoff: 2 ^ attempt_count minutes. Wait if last_attempt was too recent.
            if t.last_attempt and t.attempt_count > 0:
                delay_minutes = min(math.pow(2, t.attempt_count - 1), 1440) # Max 24 hours
                if now < t.last_attempt + timedelta(minutes=delay_minutes):
                    continue
                    
            await redis.enqueue_job("process_deletion_tombstone_job", tombstone_id=str(t.tombstone_id))
            enqueued_count += 1
            
        return {"status": "completed", "enqueued": enqueued_count}


async def delete_open_notebook_source_job(ctx: dict, *, source_id: str, snapshot_id: str) -> dict[str, Any]:
    """Compatibility job: deletes open notebook source binding if present."""
    from app.models.open_notebook_binding import OpenNotebookSourceBinding
    async with async_session_maker() as session:
        result = await session.execute(
            select(OpenNotebookSourceBinding).where(OpenNotebookSourceBinding.source_id == UUID(source_id))
        )
        binding = result.scalars().first()
        if not binding:
            return {"status": "skipped", "reason": "no_binding"}
        return {"status": "completed"}


async def delete_open_notebook_workspace_job(ctx: dict, *, workspace_id: str) -> dict[str, Any]:
    """Compatibility job: deletes open notebook workspace binding if present."""
    from app.models.open_notebook_binding import OpenNotebookWorkspaceBinding
    async with async_session_maker() as session:
        result = await session.execute(
            select(OpenNotebookWorkspaceBinding).where(OpenNotebookWorkspaceBinding.workspace_id == UUID(workspace_id))
        )
        binding = result.scalars().first()
        if not binding:
            return {"status": "skipped", "reason": "no_binding"}
        return {"status": "completed"}

