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
) -> dict[str, Any]:
    """
    Background job: synchronizes a KnowledgeMemory row from Postgres to the Neo4j Graph.

    Idempotency contract:
    - Re-running on the same knowledge_id will run a Neo4j MERGE, which safely
      updates properties without duplicating the node or edge.
    """
    k_uuid = UUID(knowledge_id)

    async with async_session_maker() as session:
        repo = KnowledgeRepository(session)
        # We don't have the owner_id in the payload, but get_knowledge requires it.
        # Let's query by knowledge_id directly.
        result = await session.execute(
            select(repo.session.info.get("model", __import__("app.models.knowledge", fromlist=["KnowledgeMemory"]).KnowledgeMemory))
            .where(__import__("app.models.knowledge", fromlist=["KnowledgeMemory"]).KnowledgeMemory.knowledge_id == k_uuid)
        )
        knowledge = result.scalars().first()

        if not knowledge:
            logger.error("sync_knowledge_to_graph_job: knowledge_id %s not found", knowledge_id)
            return {"status": "not_found", "knowledge_id": knowledge_id}

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
            await redis.publish(channel_name, json.dumps(event_data))

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
        from app.models.research import ResearchRun
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
            
        owner_id = run.owner_id
        engine_flag = run.engine
        actual_run_id = UUID(run_id)

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
    
    try:
        final_graph = None
        final_status = "completed"
        final_reason = "Engine finished normally"
        
        async for event in engine.astream_events(run_id=actual_run_id, workspace_id=UUID(workspace_id), objective=objective):
            await publish_event(event)
            status = event.get("status")
            
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
            
            # Transition state to final_status
            await lifecycle.transition_run(UUID(workspace_id), actual_run_id, final_status, {"reason": final_reason})
            await session.commit()
            
            # Run final promotion only if completed
            if final_status == "completed":
                mem_router = MemoryRouter(
                    episodic_repo=__import__("app.repositories.episodic", fromlist=["EpisodicRepository"]).EpisodicRepository(session),
                    knowledge_repo=__import__("app.repositories.knowledge", fromlist=["KnowledgeRepository"]).KnowledgeRepository(session),
                    llm_gateway=llm_gateway
                )
                graph_repo = GraphRepository(graph_store)
                research_service = ResearchService(repo, mem_router, graph_repo)
                
                if owner_id:
                    await research_service.promote_memory_candidates(UUID(workspace_id), actual_run_id, owner_id)
                await research_service.promote_graph_candidates(UUID(workspace_id), actual_run_id)

        await publish_event({"status": final_status, "message": f"Research {final_status}"})
        if final_graph and redis and final_status == "completed":
            await redis.enqueue_job(
                "project_output_graph_job",
                workspace_id=workspace_id,
                graph_dict=final_graph
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
                await lifecycle.transition_run(UUID(workspace_id), actual_run_id, "failed", {"error": str(exc)})
                await session.commit()
        except Exception as transition_exc:
            logger.warning(f"Could not transition run to failed (might already be terminal): {transition_exc}")
            
        return {"status": "failed", "workspace_id": workspace_id, "error": str(exc)}

# --------------------------------------------------------------------------- #
# project_output_graph_job
# --------------------------------------------------------------------------- #

async def project_output_graph_job(
    ctx: dict,
    *,
    workspace_id: str,
    graph_dict: dict
) -> dict[str, Any]:
    """
    Background job: Projects the final OutputGraph from the research agent into Neo4j.
    """
    from uuid import UUID
    from app.schemas.graph import OutputGraph
    from app.repositories.graph import graph_store, GraphRepository
    
    workspace_uuid = UUID(workspace_id)
    
    try:
        # Reconstruct Pydantic model
        graph = OutputGraph(**graph_dict)
        
        repo = GraphRepository(graph_store)
        await repo.project_output_graph(workspace_uuid, graph)
        
        logger.info(f"project_output_graph_job: Successfully projected graph for workspace {workspace_id}")
        return {"status": "completed", "workspace_id": workspace_id}
        
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
