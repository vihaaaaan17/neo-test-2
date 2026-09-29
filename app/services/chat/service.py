import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Tuple, Dict, Any, AsyncGenerator
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from arq.connections import ArqRedis

from app.core.database import async_session_maker
from app.models.conversation import Conversation, ConversationTurn
from app.models.open_notebook_binding import OpenNotebookConversationBinding, OpenNotebookWorkspaceBinding
from app.models.research import ResearchRun
from app.repositories.conversation import ConversationRepository
from app.repositories.workspace import WorkspaceRepository
from app.repositories.research import ResearchRepository
from app.services.research.admission import ResearchAdmissionController
from app.services.research.quota import ResearchQuotaService
from app.services.research.rate_limiter import ProviderRateLimiter
from app.integrations.open_notebook.client import OpenNotebookClient
from app.integrations.open_notebook.ground_engine import OpenNotebookGroundEngine
from app.schemas.chat import TurnCreate
from app.services.chat.events import (
    ChatEventRepository,
    ChatEventService,
    TurnEventBroker,
    format_sse_event
)

logger = logging.getLogger(__name__)


class ChatService:
    """
    Coordinates turn submission, mode dispatching (Ground vs Research),
    transactional sequence allocation, transparent session recovery,
    SSE streaming, reconnect event replay, and turn finalization.
    """
    _running_tasks: Dict[UUID, asyncio.Task] = {}

    def __init__(
        self,
        db: AsyncSession,
        conv_repo: Optional[ConversationRepository] = None,
        workspace_repo: Optional[WorkspaceRepository] = None,
        research_repo: Optional[ResearchRepository] = None,
        admission_controller: Optional[ResearchAdmissionController] = None,
        arq_redis: Optional[ArqRedis] = None,
        open_notebook_client: Optional[OpenNotebookClient] = None,
        ground_engine: Optional[OpenNotebookGroundEngine] = None,
        event_repo: Optional[ChatEventRepository] = None,
    ):
        self.db = db
        self.conv_repo = conv_repo or ConversationRepository(db)
        self.workspace_repo = workspace_repo or WorkspaceRepository(db)
        self.research_repo = research_repo or ResearchRepository(db)
        self.arq_redis = arq_redis
        self.admission_controller = admission_controller
        self.open_notebook_client = open_notebook_client or OpenNotebookClient()
        self.ground_engine = ground_engine
        self.event_repo = event_repo or ChatEventRepository(db)
        self.event_service = ChatEventService(self.event_repo, arq_redis)

    async def submit_turn(
        self,
        workspace_id: UUID,
        conversation_id: UUID,
        owner_id: UUID,
        turn_create: TurnCreate,
        stream: bool = False
    ) -> ConversationTurn:
        """
        Submits and executes a conversation turn synchronously (or 202 for research).
        Validates workspace ownership, allocates monotonic sequence under lock,
        and dispatches to the selected engine mode.
        """
        # 1. Validate workspace and conversation
        workspace = await self.workspace_repo.get_workspace(workspace_id, owner_id)
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found or access denied"
            )

        conversation = await self.conv_repo.get_conversation(workspace_id, conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        if conversation.owner_id != owner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to conversation"
            )
        if conversation.status == "archived":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot submit turn to archived conversation"
            )

        # 2. Idempotency check via client_request_id
        if turn_create.client_request_id:
            existing = await self.conv_repo.get_turn_by_client_request_id(
                conversation_id=conversation_id,
                client_request_id=turn_create.client_request_id
            )
            if existing:
                logger.info(
                    "Idempotency hit for conversation %s client_request_id %s (turn_id=%s)",
                    conversation_id, turn_create.client_request_id, existing.turn_id
                )
                return existing

        # 3. Monotonic sequence allocation under row-level lock (FOR UPDATE)
        sequence = await self.conv_repo.allocate_turn_sequence(conversation_id)

        # 4. Insert initial turn record
        turn = await self.conv_repo.append_turn(
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            owner_id=owner_id,
            mode=turn_create.mode,
            user_message=turn_create.message,
            sequence=sequence,
            client_request_id=turn_create.client_request_id,
            source_scope=turn_create.source_scope
        )

        # 5. Dispatch by mode
        if turn_create.mode == "ground":
            return await self._execute_ground_turn(workspace, conversation, turn, stream=stream)
        elif turn_create.mode == "research":
            return await self._execute_research_turn(workspace, conversation, turn, stream=stream, turn_create=turn_create)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported turn mode: {turn_create.mode}"
            )

    async def stream_turn(
        self,
        workspace_id: UUID,
        conversation_id: UUID,
        owner_id: UUID,
        turn_create: TurnCreate
    ) -> AsyncGenerator[str, None]:
        """
        Submits a turn and returns an async generator streaming its events via SSE.
        Background tasks run independently of HTTP client disconnects.
        """
        # 1. Validate workspace and conversation
        workspace = await self.workspace_repo.get_workspace(workspace_id, owner_id)
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found or access denied"
            )

        conversation = await self.conv_repo.get_conversation(workspace_id, conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        if conversation.owner_id != owner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to conversation"
            )
        if conversation.status == "archived":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot submit turn to archived conversation"
            )

        # 2. Idempotency check via client_request_id
        if turn_create.client_request_id:
            existing = await self.conv_repo.get_turn_by_client_request_id(
                conversation_id=conversation_id,
                client_request_id=turn_create.client_request_id
            )
            if existing:
                return self.stream_turn_events(existing.turn_id)

        # 3. Monotonic sequence allocation under row-level lock (FOR UPDATE)
        sequence = await self.conv_repo.allocate_turn_sequence(conversation_id)

        # 4. Insert initial turn record
        turn = await self.conv_repo.append_turn(
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            owner_id=owner_id,
            mode=turn_create.mode,
            user_message=turn_create.message,
            sequence=sequence,
            client_request_id=turn_create.client_request_id,
            source_scope=turn_create.source_scope
        )

        # 5. Dispatch background execution and return stream generator
        if turn_create.mode == "ground":
            bg_task = asyncio.create_task(
                self._execute_ground_stream_background(
                    workspace_id=workspace.workspace_id,
                    conversation_id=conversation.conversation_id,
                    turn_id=turn.turn_id,
                    user_message=turn_create.message
                )
            )
            ChatService._running_tasks[turn.turn_id] = bg_task
            bg_task.add_done_callback(lambda t: ChatService._running_tasks.pop(turn.turn_id, None))
            return self.stream_turn_events(turn.turn_id)
        elif turn_create.mode == "research":
            engine = workspace.research_engine or "open_deep_research"
            if turn_create.research_options:
                engine = turn_create.research_options.get("engine") or engine
            admission_controller = self.admission_controller or ResearchAdmissionController(
                quota_service=ResearchQuotaService(self.research_repo),
                rate_limiter=ProviderRateLimiter(self.arq_redis),
                repository=self.research_repo
            )
            base_commit = getattr(workspace, "active_commit_id", None)
            run = await admission_controller.admit_research_run(
                workspace_id=workspace.workspace_id,
                owner_id=owner_id,
                objective=turn_create.message,
                engine=engine,
                conversation_id=conversation.conversation_id,
                turn_id=turn.turn_id,
                base_commit_id=base_commit
            )

            # Assemble Research context and snapshot context_version before starting
            from app.services.chat.context import build_research_context
            research_opts = getattr(turn_create, "research_options", None) or {}
            token_budget = research_opts.get("token_budget", 8000)
            working_memory = research_opts.get("working_memory")
            output_graph = research_opts.get("output_graph")

            research_ctx = await build_research_context(
                session=self.db,
                workspace_id=workspace.workspace_id,
                conversation_id=conversation.conversation_id,
                query=turn_create.message,
                token_budget=token_budget,
                working_memory=working_memory,
                output_graph=output_graph
            )
            merged_context = {}
            if hasattr(research_ctx, "context_version") and hasattr(research_ctx.context_version, "model_dump"):
                v_dump = research_ctx.context_version.model_dump(mode="json")
                if isinstance(v_dump, dict):
                    merged_context.update(v_dump)
            if hasattr(research_ctx, "model_dump"):
                try:
                    m_dump = research_ctx.model_dump(mode="json")
                    if isinstance(m_dump, dict):
                        merged_context = {**m_dump, **merged_context}
                except Exception:
                    pass

            context_version_bundle = {
                "research_context": merged_context
            }

            await self.conv_repo.set_turn_status(
                turn_id=turn.turn_id,
                status="running",
                research_run_id=run.run_id,
                context_version=context_version_bundle,
                started_at=datetime.now(timezone.utc)
            )

            if self.arq_redis:
                job_id = str(uuid.uuid4())
                await self.arq_redis.enqueue_job(
                    "run_research_agent_job",
                    workspace_id=str(workspace.workspace_id),
                    objective=turn_create.message,
                    run_id=str(run.run_id),
                    research_context=merged_context,
                    _job_id=job_id,
                    _queue_name="research-standard"
                )

            asyncio.create_task(
                self._bridge_research_events_background(
                    turn_id=turn.turn_id,
                    run_id=run.run_id
                )
            )
            return self.stream_turn_events(turn.turn_id)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported turn mode: {turn_create.mode}"
            )

    async def stream_turn_events(
        self,
        turn_id: UUID,
        after_sequence: int = 0,
    ) -> AsyncGenerator[str, None]:
        """
        Unified SSE generator — supports reconnect replay via Last-Event-ID.

        Protocol:
          1. Subscribe to Redis pubsub and local broker *before* any DB read
             so no event published after subscription can be missed.
          2. Replay PostgreSQL ChatEvents with sequence > after_sequence,
             emitting ``id: <sequence>`` on every frame.
          3. If a terminal event ('done', 'error', 'cancelled') is found in
             the replay, close immediately without opening the live loop.
          4. Drain live messages from local broker (with a Redis pubsub
             fallback when arq_redis supports pubsub), deduplicating by
             sequence against last_seq.  Emit keep-alive comments on timeout.
          5. Exit cleanly on any terminal event_type.
        """
        _TERMINAL = frozenset({"done", "error", "cancelled"})
        channel = f"turn_events:{turn_id}"

        # ------------------------------------------------------------------
        # Step 0: Subscribe BEFORE any DB read to avoid a missed-event race.
        # ------------------------------------------------------------------
        local_q = TurnEventBroker.subscribe_local(channel)
        pubsub = None
        if self.arq_redis and hasattr(self.arq_redis, "pubsub"):
            try:
                _ps = self.arq_redis.pubsub()
                await asyncio.wait_for(_ps.subscribe(channel), timeout=1.0)
                pubsub = _ps
            except (asyncio.TimeoutError, Exception) as _ps_err:
                logger.debug("Redis pubsub unavailable for %s: %s", channel, _ps_err)
                pubsub = None

        try:
            # ---------------------------------------------------------------
            # Step 1: Replay persisted events (catch-up / reconnect support).
            # ---------------------------------------------------------------
            last_seq: int = after_sequence
            existing_events = await self.event_repo.list_events_after(
                turn_id, after_sequence=after_sequence
            )
            for ev in existing_events:
                yield format_sse_event(ev.event_type, ev.payload, event_id=ev.sequence)
                last_seq = max(last_seq, ev.sequence)
                if ev.event_type in _TERMINAL:
                    return

            # ---------------------------------------------------------------
            # Step 2: Stream live events until terminal.
            # ---------------------------------------------------------------
            while True:
                msg: Optional[Dict[str, Any]] = None

                # 2a. Prefer in-process local broker (zero-latency on same node)
                try:
                    msg = await asyncio.wait_for(local_q.get(), timeout=10.0)
                except asyncio.TimeoutError:
                    pass

                # 2b. If local queue timed-out, poll Redis pubsub once
                if msg is None and pubsub is not None:
                    try:
                        raw_msg = await asyncio.wait_for(
                            pubsub.get_message(ignore_subscribe_messages=True, timeout=0.0),
                            timeout=0.5
                        )
                        if raw_msg and raw_msg.get("type") == "message":
                            raw_data = raw_msg.get("data", b"")
                            if isinstance(raw_data, bytes):
                                raw_data = raw_data.decode("utf-8")
                            msg = json.loads(raw_data) if raw_data else None
                    except (asyncio.TimeoutError, Exception) as _redis_err:
                        logger.debug("Redis pubsub poll error: %s", _redis_err)

                # 2c. Keep-alive + DB safety-net when both sources are idle
                if msg is None:
                    yield ": keep-alive\n\n"
                    try:
                        async with async_session_maker() as _check_s:
                            _ch_repo = ChatEventRepository(_check_s)
                            recent = await _ch_repo.list_events_after(
                                turn_id, after_sequence=last_seq
                            )
                            for ev in recent:
                                yield format_sse_event(
                                    ev.event_type, ev.payload, event_id=ev.sequence
                                )
                                last_seq = max(last_seq, ev.sequence)
                                if ev.event_type in _TERMINAL:
                                    return
                    except Exception as _db_err:
                        logger.debug("DB safety-net check failed: %s", _db_err)
                    continue

                # 2d. Deduplicate and emit
                seq = msg.get("sequence", 0)
                if seq > last_seq:
                    last_seq = seq
                    ev_type = msg.get("event_type", "message")
                    payload = msg.get("payload", {})
                    yield format_sse_event(ev_type, payload, event_id=seq)
                    if ev_type in _TERMINAL:
                        break

        finally:
            TurnEventBroker.unsubscribe_local(channel, local_q)
            if pubsub is not None:
                try:
                    await pubsub.unsubscribe(channel)
                    await pubsub.close()
                except Exception:
                    pass

    async def _execute_ground_stream_background(
        self,
        workspace_id: UUID,
        conversation_id: UUID,
        turn_id: UUID,
        user_message: str
    ):
        """
        Executes Ground turn in background with independent DB session.
        Delegates exclusively through OpenNotebookGroundEngine. Survives client disconnects.
        """
        async with async_session_maker() as session:
            event_repo = ChatEventRepository(session)
            event_service = ChatEventService(event_repo, self.arq_redis)
            conv_repo = ConversationRepository(session)

            # Record running status event
            await event_service.record_and_publish(
                turn_id=turn_id,
                event_type="status_change",
                payload={"status": "running"}
            )
            await conv_repo.set_turn_status(
                turn_id=turn_id,
                status="running",
                started_at=datetime.now(timezone.utc)
            )

            # Assemble Ground context adhering strictly to GroundContextPolicy
            from app.services.chat.context import build_ground_context
            ground_ctx = await build_ground_context(
                session=session,
                workspace_id=workspace_id,
                conversation_id=conversation_id,
                query=user_message,
                explicit_scope=None
            )

            engine = self.ground_engine or OpenNotebookGroundEngine(
                workspace_id=workspace_id,
                client=self.open_notebook_client
            )

            full_answer: List[str] = []
            evidence_refs: List[Any] = []
            prov_status: str = "full"

            try:
                async for chunk in engine.astream(
                    workspace_id=workspace_id,
                    conversation_id=conversation_id,
                    turn_id=turn_id,
                    query=user_message,
                    db=session,
                    ground_context=ground_ctx
                ):
                    ev_type = chunk.get("event") or chunk.get("type") or "token"
                    ev_data = chunk.get("data") or {}

                    if ev_type in ["token", "answer"]:
                        token = ev_data.get("content") or ev_data.get("token") or chunk.get("content") or ""
                        if token:
                            full_answer.append(token)
                            await event_service.record_and_publish(turn_id, "token", {"content": token})
                    elif ev_type == "strategy":
                        await event_service.record_and_publish(turn_id, "strategy", ev_data)
                    elif ev_type == "citation":
                        evidence_refs = chunk.get("evidence") or ev_data.get("evidence") or []
                        prov_status = chunk.get("provenance_status") or ev_data.get("provenance_status") or "full"
                        formatted_ev = [e if isinstance(e, dict) else {"source_id": str(e)} for e in evidence_refs]
                        await event_service.record_and_publish(
                            turn_id,
                            "citation",
                            {"evidence": formatted_ev, "provenance_status": prov_status}
                        )
                    elif ev_type == "done":
                        if not full_answer:
                            ans = chunk.get("answer") or ev_data.get("answer") or ""
                            if ans:
                                full_answer.append(ans)
                        if not evidence_refs:
                            evidence_refs = chunk.get("evidence") or ev_data.get("evidence") or []
                        prov_status = chunk.get("provenance_status") or ev_data.get("provenance_status") or prov_status

                final_answer_text = "".join(full_answer)
                formatted_evidence_refs = [
                    e if isinstance(e, dict) else str(e)
                    for e in evidence_refs
                ]

                await conv_repo.set_turn_status(
                    turn_id=turn_id,
                    status="completed",
                    assistant_message=final_answer_text,
                    ground_evidence_refs=formatted_evidence_refs,
                    context_version={"ground_context": ground_ctx.model_dump(mode="json")},
                    completed_at=datetime.now(timezone.utc)
                )
                await event_service.record_and_publish(
                    turn_id=turn_id,
                    event_type="done",
                    payload={
                        "status": "completed",
                        "assistant_message": final_answer_text,
                        "ground_evidence_refs": formatted_evidence_refs,
                        "provenance_status": prov_status
                    }
                )
            except asyncio.CancelledError:
                logger.info("Ground turn %s execution was cancelled.", turn_id)
                raise
            except HTTPException as e:
                error_detail = str(e.detail)
                await conv_repo.set_turn_status(
                    turn_id=turn_id,
                    status="failed",
                    error_code="upstream_ground_failure",
                    error_message=error_detail,
                    completed_at=datetime.now(timezone.utc)
                )
                await event_service.record_and_publish(
                    turn_id=turn_id,
                    event_type="error",
                    payload={"message": error_detail}
                )
                await event_service.record_and_publish(
                    turn_id=turn_id,
                    event_type="done",
                    payload={"status": "failed", "error": error_detail}
                )
            except Exception as e:
                logger.error(f"Background ground execution failed: {e}", exc_info=True)
                error_detail = str(e)
                await conv_repo.set_turn_status(
                    turn_id=turn_id,
                    status="failed",
                    error_code="ground_execution_error",
                    error_message=error_detail,
                    completed_at=datetime.now(timezone.utc)
                )
                await event_service.record_and_publish(
                    turn_id=turn_id,
                    event_type="error",
                    payload={"message": error_detail}
                )
                await event_service.record_and_publish(
                    turn_id=turn_id,
                    event_type="done",
                    payload={"status": "failed", "error": error_detail}
                )

    async def _bridge_research_events_background(
        self,
        turn_id: UUID,
        run_id: UUID
    ):
        """
        Bridges Redis Pub/Sub research_events:{run_id} to turn_events:{turn_id} and chat_events table.
        Runs independently in background, surviving client disconnect.
        """
        async with async_session_maker() as session:
            event_repo = ChatEventRepository(session)
            event_service = ChatEventService(event_repo, self.arq_redis)
            conv_repo = ConversationRepository(session)

            # Record running status event
            await event_service.record_and_publish(
                turn_id=turn_id,
                event_type="status_change",
                payload={"status": "running", "research_run_id": str(run_id)}
            )

            # Subscribe to Redis pubsub if available
            pubsub = None
            if self.arq_redis and hasattr(self.arq_redis, "pubsub"):
                try:
                    pubsub = self.arq_redis.pubsub()
                    await pubsub.subscribe(f"research_events:{run_id}")
                except Exception as e:
                    logger.warning(f"Failed to subscribe to Redis research_events:{run_id}: {e}")
                    pubsub = None

            # Also listen to in-process local queue for research_events:{run_id}
            local_q = TurnEventBroker.subscribe_local(f"research_events:{run_id}")

            try:
                finished = False
                while not finished:
                    message_data = None
                    if pubsub:
                        try:
                            msg = await asyncio.wait_for(
                                pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0),
                                timeout=1.0
                            )
                            if msg and msg.get("type") == "message":
                                raw_data = msg.get("data")
                                if isinstance(raw_data, bytes):
                                    raw_data = raw_data.decode("utf-8")
                                message_data = json.loads(raw_data) if isinstance(raw_data, str) else raw_data
                        except asyncio.TimeoutError:
                            pass

                    if not message_data and not local_q.empty():
                        message_data = await local_q.get()

                    if not message_data:
                        # Polling fallback: check ResearchRun in DB
                        await asyncio.sleep(0.1)
                        rr = await session.get(ResearchRun, run_id)
                        if rr and rr.status in ["completed", "failed", "cancelled"]:
                            message_data = {
                                "event_type": "status_change",
                                "payload": {"status": rr.status}
                            }

                    if message_data:
                        raw_ev_type = message_data.get("event_type", "progress")
                        payload = message_data.get("payload", {})

                        if raw_ev_type in ["step", "phase_change", "log", "metric", "progress"]:
                            mapped_type = "progress"
                        elif raw_ev_type in ["token", "chunk"]:
                            mapped_type = "token"
                        elif raw_ev_type == "scratchpad_entry":
                            mapped_type = "scratchpad_entry"
                        elif raw_ev_type == "status_change":
                            st = payload.get("status")
                            if st in ["completed", "failed", "cancelled"]:
                                mapped_type = "done"
                                finished = True
                            else:
                                mapped_type = "status_change"
                        elif raw_ev_type == "done":
                            mapped_type = "done"
                            finished = True
                        else:
                            mapped_type = "progress"

                        await event_service.record_and_publish(turn_id, mapped_type, payload)

                        if finished:
                            final_status = payload.get("status", "completed")
                            await conv_repo.set_turn_status(
                                turn_id=turn_id,
                                status=final_status,
                                completed_at=datetime.now(timezone.utc)
                            )
                            break
            finally:
                TurnEventBroker.unsubscribe_local(f"research_events:{run_id}", local_q)
                if pubsub:
                    try:
                        await pubsub.unsubscribe(f"research_events:{run_id}")
                        await pubsub.close()
                    except Exception:
                        pass

    async def _execute_ground_turn(
        self,
        workspace: Any,
        conversation: Conversation,
        turn: ConversationTurn,
        stream: bool = False
    ) -> ConversationTurn:
        """
        Executes a Ground mode turn against Open Notebook with 1-time transparent 409 session rehydration.
        Does NOT write to knowledge store or sync to Neo4j.
        """
        await self.conv_repo.set_turn_status(
            turn_id=turn.turn_id,
            status="running",
            started_at=datetime.now(timezone.utc)
        )
        await self.event_service.record_and_publish(
            turn_id=turn.turn_id,
            event_type="status_change",
            payload={"status": "running"}
        )

        # Assemble Ground context adhering strictly to GroundContextPolicy
        from app.services.chat.context import build_ground_context
        ground_ctx = await build_ground_context(
            session=self.db,
            workspace_id=workspace.workspace_id,
            conversation_id=conversation.conversation_id,
            query=turn.user_message,
            explicit_scope=turn.source_scope
        )

        # 1. Check if custom ground_engine is injected or if Open Notebook is disabled
        from app.core.config import settings
        from app.integrations.open_notebook.ground_engine import OpenNotebookGroundEngine

        engine_to_run = self.ground_engine or OpenNotebookGroundEngine(
            workspace_id=workspace.workspace_id,
            client=self.open_notebook_client
        )
        if not settings.OPEN_NOTEBOOK_ENABLED and self.ground_engine is None:
            from app.services.ground.factory import get_ground_engine
            engine_to_run = await get_ground_engine()

        try:
            import inspect
            sig = inspect.signature(engine_to_run.run)
            kwargs = {"workspace_id": workspace.workspace_id, "query": turn.user_message}
            if "db" in sig.parameters:
                kwargs["db"] = self.db
            if "conversation_id" in sig.parameters:
                kwargs["conversation_id"] = conversation.conversation_id
            if "turn_id" in sig.parameters:
                kwargs["turn_id"] = turn.turn_id
            if "source_scope" in sig.parameters:
                kwargs["source_scope"] = turn.source_scope
            if "ground_context" in sig.parameters:
                kwargs["ground_context"] = ground_ctx

            state = await engine_to_run.run(**kwargs)

            if not state.get("is_grounded", False):
                await self.conv_repo.set_turn_status(
                    turn_id=turn.turn_id,
                    status="failed",
                    error_code="ungrounded_answer",
                    error_message="Unable to generate a grounded answer from the provided context.",
                    completed_at=datetime.now(timezone.utc)
                )
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Unable to generate a grounded answer from the provided context."
                )

            answer = state.get("answer", "")
            raw_ev = state.get("evidence", []) or [doc["id"] for doc in state.get("context_docs", []) if "id" in doc]
            evidence_refs = []
            for e in raw_ev:
                if isinstance(e, dict):
                    evidence_refs.append(e)
                else:
                    try:
                        evidence_refs.append(UUID(str(e)))
                    except Exception:
                        evidence_refs.append(str(e))
            prov_status = state.get("provenance_status", "full")

            formatted_evidence_refs = [
                e if isinstance(e, dict) else str(e)
                for e in evidence_refs
            ]

            await self.event_service.record_and_publish(
                turn_id=turn.turn_id,
                event_type="ground_answer",
                payload={"answer": answer, "evidence": formatted_evidence_refs, "provenance_status": prov_status}
            )
            await self.event_service.record_and_publish(
                turn_id=turn.turn_id,
                event_type="token",
                payload={"content": answer}
            )
            if evidence_refs:
                await self.event_service.record_and_publish(
                    turn_id=turn.turn_id,
                    event_type="citation",
                    payload={"evidence": formatted_evidence_refs, "provenance_status": prov_status}
                )
            await self.event_service.record_and_publish(
                turn_id=turn.turn_id,
                event_type="done",
                payload={
                    "status": "completed",
                    "assistant_message": answer,
                    "ground_evidence_refs": formatted_evidence_refs,
                    "provenance_status": prov_status
                }
            )

            completed_turn = await self.conv_repo.set_turn_status(
                turn_id=turn.turn_id,
                status="completed",
                assistant_message=answer,
                ground_evidence_refs=formatted_evidence_refs,
                context_version={"ground_context": ground_ctx.model_dump(mode="json")},
                completed_at=datetime.now(timezone.utc)
            )
            return completed_turn
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Ground engine run failed: %s", e, exc_info=True)
            await self.conv_repo.set_turn_status(
                turn_id=turn.turn_id,
                status="failed",
                error_code="ground_execution_error",
                error_message=str(e),
                completed_at=datetime.now(timezone.utc)
            )
            raise HTTPException(status_code=500, detail=str(e))

    async def _rehydrate_open_notebook_session(
        self,
        workspace_id: UUID,
        conversation_id: UUID,
        notebook_id: str
    ) -> str:
        """
        Creates a new Open Notebook chat session and updates the binding for the conversation.
        """
        new_session_id = await self.open_notebook_client.create_chat_session(notebook_id)

        stmt = select(OpenNotebookConversationBinding).where(
            OpenNotebookConversationBinding.conversation_id == conversation_id
        )
        res = await self.db.execute(stmt)
        binding = res.scalars().first()
        if binding:
            binding.open_notebook_session_id = new_session_id
            binding.updated_at = datetime.now(timezone.utc)
        else:
            binding = OpenNotebookConversationBinding(
                conversation_id=conversation_id,
                open_notebook_session_id=new_session_id
            )
            self.db.add(binding)

        await self.db.commit()
        return new_session_id

    async def _execute_research_turn(
        self,
        workspace: Any,
        conversation: Conversation,
        turn: ConversationTurn,
        stream: bool = False,
        turn_create: Optional[TurnCreate] = None
    ) -> ConversationTurn:
        """
        Admits research run, links to turn, enqueues ARQ job, and returns running turn (HTTP 202).
        """
        engine = "open_deep_research"
        engine_revision = None
        if turn_create and turn_create.research_options:
            engine = turn_create.research_options.get("engine") or engine
            engine_revision = turn_create.research_options.get("engine_revision")
        elif getattr(workspace, "research_engine", None):
            engine = workspace.research_engine

        admission_controller = self.admission_controller or ResearchAdmissionController(
            quota_service=ResearchQuotaService(self.research_repo),
            rate_limiter=ProviderRateLimiter(self.arq_redis),
            repository=self.research_repo
        )

        # 1. Admit Research Run
        base_commit = getattr(workspace, "active_commit_id", None)
        run = await admission_controller.admit_research_run(
            workspace_id=workspace.workspace_id,
            owner_id=turn.owner_id,
            objective=turn.user_message,
            engine=engine,
            engine_revision=engine_revision,
            conversation_id=conversation.conversation_id,
            turn_id=turn.turn_id,
            base_commit_id=base_commit
        )

        # Assemble Research context and snapshot context_version before enqueueing
        from app.services.chat.context import build_research_context
        research_opts = getattr(turn_create, "research_options", None) or {}
        token_budget = research_opts.get("token_budget", 8000)
        working_memory = research_opts.get("working_memory")
        output_graph = research_opts.get("output_graph")

        research_ctx = await build_research_context(
            session=self.db,
            workspace_id=workspace.workspace_id,
            conversation_id=conversation.conversation_id,
            query=turn.user_message,
            token_budget=token_budget,
            working_memory=working_memory,
            output_graph=output_graph
        )
        merged_context = {}
        if hasattr(research_ctx, "context_version") and hasattr(research_ctx.context_version, "model_dump"):
            v_dump = research_ctx.context_version.model_dump(mode="json")
            if isinstance(v_dump, dict):
                merged_context.update(v_dump)
        if hasattr(research_ctx, "model_dump"):
            try:
                m_dump = research_ctx.model_dump(mode="json")
                if isinstance(m_dump, dict):
                    merged_context = {**m_dump, **merged_context}
            except Exception:
                pass

        context_version_bundle = {
            "research_context": merged_context
        }

        # 2. Update Turn to running with research_run_id and context_version snapshot
        running_turn = await self.conv_repo.set_turn_status(
            turn_id=turn.turn_id,
            status="running",
            research_run_id=run.run_id,
            context_version=context_version_bundle,
            started_at=datetime.now(timezone.utc)
        )
        await self.event_service.record_and_publish(
            turn_id=turn.turn_id,
            event_type="status_change",
            payload={"status": "running", "research_run_id": str(run.run_id)}
        )

        # 3. Enqueue ARQ job to queue research-standard
        if self.arq_redis:
            job_id = str(uuid.uuid4())
            await self.arq_redis.enqueue_job(
                "run_research_agent_job",
                workspace_id=str(workspace.workspace_id),
                objective=turn.user_message,
                run_id=str(run.run_id),
                research_context=merged_context,
                _job_id=job_id,
                _queue_name="research-standard"
            )

        return running_turn

    async def get_turn(
        self,
        workspace_id: UUID,
        conversation_id: UUID,
        turn_id: UUID,
        owner_id: UUID
    ) -> ConversationTurn:
        """
        Retrieves a single turn with tenant access validation.
        """
        conversation = await self.conv_repo.get_conversation(workspace_id, conversation_id)
        if not conversation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
        if conversation.owner_id != owner_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        turn = await self.conv_repo.get_turn(workspace_id, conversation_id, turn_id)
        if not turn:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turn not found")
        return turn

    async def list_turns(
        self,
        workspace_id: UUID,
        conversation_id: UUID,
        owner_id: UUID,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[ConversationTurn], int]:
        """
        Lists turns in a conversation ordered by sequence.
        """
        conversation = await self.conv_repo.get_conversation(workspace_id, conversation_id)
        if not conversation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
        if conversation.owner_id != owner_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        return await self.conv_repo.list_turns(
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            limit=limit,
            offset=offset
        )

    async def get_turn_events(
        self,
        workspace_id: UUID,
        conversation_id: UUID,
        turn_id: UUID,
        owner_id: UUID,
        after_sequence: int = 0
    ):
        """
        Retrieves historical events for reconnect replay, verifying workspace ownership
        and conversation tenant isolation.
        """
        workspace = await self.workspace_repo.get_workspace(workspace_id, owner_id)
        if not workspace:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found or access denied")

        conversation = await self.conv_repo.get_conversation(workspace_id, conversation_id)
        if not conversation or conversation.owner_id != owner_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found or access denied")

        turn = await self.conv_repo.get_turn(workspace_id, conversation_id, turn_id)
        if not turn:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turn not found")

        return await self.event_service.get_turn_events(turn_id, after_sequence=after_sequence)

    async def cancel_turn(
        self,
        workspace_id: UUID,
        conversation_id: UUID,
        turn_id: UUID,
        owner_id: UUID
    ) -> ConversationTurn:
        """
        Cancels an in-flight conversation turn (Ground or Research mode).
        Cascades cancellation to underlying execution engines and publishes 'turn.cancelled'.
        """
        # 1. Validate workspace and conversation ownership
        workspace = await self.workspace_repo.get_workspace(workspace_id, owner_id)
        if not workspace:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found or access denied")

        conversation = await self.conv_repo.get_conversation(workspace_id, conversation_id)
        if not conversation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
        if conversation.owner_id != owner_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        turn = await self.conv_repo.get_turn(workspace_id, conversation_id, turn_id)
        if not turn:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turn not found")

        if turn.status == "cancelled":
            return turn

        if turn.status in ["completed", "failed"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel turn with status '{turn.status}'"
            )

        # 2. Cancel based on mode
        if turn.mode == "ground":
            task = ChatService._running_tasks.pop(turn_id, None)
            if task and not task.done():
                task.cancel()

        elif turn.mode == "research":
            if turn.research_run_id:
                run = await self.research_repo.get_run(workspace_id, turn.research_run_id)
                if run and run.status not in ["completed", "failed", "cancelled"]:
                    from app.services.research.lifecycle import ResearchLifecycleService
                    lifecycle = ResearchLifecycleService(self.research_repo)
                    try:
                        await lifecycle.transition_run(
                            workspace_id=workspace_id,
                            run_id=turn.research_run_id,
                            target_status="cancelled",
                            metadata={"reason": "Cancelled by user via turn cancellation endpoint"}
                        )
                    except Exception as e:
                        logger.warning("Failed to transition research run %s to cancelled: %s", turn.research_run_id, e)
                        run.status = "cancelled"
                        await self.db.commit()

                    # Notify via Redis for cooperative cancellation in worker engine
                    if self.arq_redis:
                        try:
                            cancel_msg = json.dumps({
                                "event_type": "cancelled",
                                "status": "cancelled",
                                "run_id": str(turn.research_run_id),
                                "reason": "Cancelled by user"
                            })
                            await self.arq_redis.publish(f"research_cancellation:{turn.research_run_id}", cancel_msg)
                            await self.arq_redis.publish(f"research_events:{turn.research_run_id}", cancel_msg)
                        except Exception as pub_err:
                            logger.warning("Failed to publish cancellation message to Redis: %s", pub_err)

        # 3. Update ConversationTurn status to cancelled
        cancelled_turn = await self.conv_repo.set_turn_status(
            turn_id=turn_id,
            status="cancelled",
            completed_at=datetime.now(timezone.utc)
        )

        # 4. Synchronously record and publish turn.cancelled and done
        await self.event_service.record_and_publish(
            turn_id=turn_id,
            event_type="turn.cancelled",
            payload={"status": "cancelled", "reason": "Cancelled by user"}
        )
        await self.event_service.record_and_publish(
            turn_id=turn_id,
            event_type="done",
            payload={"status": "cancelled", "reason": "Cancelled by user"}
        )

        return cancelled_turn
