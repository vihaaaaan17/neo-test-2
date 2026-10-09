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
from app.schemas.chat import (
    TurnCreate,
    ChatEventType,
    EVENT_TURN_RESEARCH_STARTED,
    EVENT_TURN_CANCELLED,
    EVENT_STATUS_CHANGE,
    EVENT_GROUND_ANSWER,
    EVENT_TOKEN,
    EVENT_CITATION,
    EVENT_DONE,
    EVENT_ERROR
)
from app.services.chat.events import (
    ChatEventRepository,
    ChatEventService,
    TurnEventBroker,
    format_sse_event
)

logger = logging.getLogger(__name__)


def resolve_research_routing(research_options: Optional[Dict[str, Any]]) -> Tuple[str, Optional[str]]:
    """
    (routing_mode, engine) for a Research turn. `routing_mode` "auto" (the default) lets the EngineRouter choose;
    naming an engine without a routing_mode means an explicit override. Validation happens at admission.
    """
    opts = research_options or {}
    engine = opts.get("engine") or None
    mode = opts.get("routing_mode") or ("explicit" if engine else "auto")
    return mode, engine


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
        # 0. Immediate validation before any DB row is created (Gate 1)
        if not turn_create.mode or turn_create.mode not in ("ground", "research"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported turn mode: {turn_create.mode}"
            )
        if not turn_create.message or not turn_create.message.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Turn message cannot be empty"
            )

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

        # 1b. Resolve the Ground source scope BEFORE a turn row exists: an invalid or foreign scope is a 400 that can
        #     never leave a turn behind to lock the conversation. `selected_source_ids` is the documented alias.
        if turn_create.mode == "ground":
            requested_scope = turn_create.source_scope or turn_create.selected_source_ids
            if requested_scope:
                from app.services.chat.context import resolve_ground_source_scope
                turn_create.source_scope = await resolve_ground_source_scope(self.db, workspace_id, requested_scope)

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

        # 3. Row-lock conversation and enforce one-running-turn invariant (Gate 2)
        await self.conv_repo.lock_conversation(conversation_id)
        active_turn = await self.conv_repo.get_active_turn(conversation_id)
        if active_turn is not None:
            status_val = getattr(active_turn, "status", None)
            if isinstance(status_val, str) and status_val in ("pending", "running"):
                # Only a turn that provably cannot still be executing is recovered; a live one keeps the 409.
                if not await self._recover_stale_active_turn(active_turn):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="conversation_turn_in_progress"
                    )

        # 4. Monotonic sequence allocation under row-level lock (FOR UPDATE)
        sequence = await self.conv_repo.allocate_turn_sequence(conversation_id)

        # 5. Insert initial turn record
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

        # 6. An explicit request to compile the study session is handled by the StudyReportCompiler (either mode).
        from app.services.research.study_report import is_study_report_request
        if is_study_report_request(turn_create.message):
            return await self._execute_study_report_turn(workspace, conversation, turn)

        # 7. Dispatch by mode
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
        # 0. Immediate validation before any DB row is created (Gate 1)
        if not turn_create.mode or turn_create.mode not in ("ground", "research"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported turn mode: {turn_create.mode}"
            )
        if not turn_create.message or not turn_create.message.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Turn message cannot be empty"
            )

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

        # 1b. Resolve the Ground source scope BEFORE a turn row exists: an invalid or foreign scope is a 400 that can
        #     never leave a turn behind to lock the conversation. `selected_source_ids` is the documented alias.
        if turn_create.mode == "ground":
            requested_scope = turn_create.source_scope or turn_create.selected_source_ids
            if requested_scope:
                from app.services.chat.context import resolve_ground_source_scope
                turn_create.source_scope = await resolve_ground_source_scope(self.db, workspace_id, requested_scope)

        # 2. Idempotency check via client_request_id
        if turn_create.client_request_id:
            existing = await self.conv_repo.get_turn_by_client_request_id(
                conversation_id=conversation_id,
                client_request_id=turn_create.client_request_id
            )
            if existing:
                return self.stream_turn_events(existing.turn_id)

        # 3. Row-lock conversation and enforce one-running-turn invariant (Gate 2)
        await self.conv_repo.lock_conversation(conversation_id)
        active_turn = await self.conv_repo.get_active_turn(conversation_id)
        if active_turn is not None:
            status_val = getattr(active_turn, "status", None)
            if isinstance(status_val, str) and status_val in ("pending", "running"):
                # Only a turn that provably cannot still be executing is recovered; a live one keeps the 409.
                if not await self._recover_stale_active_turn(active_turn):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="conversation_turn_in_progress"
                    )

        # 4. Monotonic sequence allocation under row-level lock (FOR UPDATE)
        sequence = await self.conv_repo.allocate_turn_sequence(conversation_id)

        # 5. Insert initial turn record
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

        # 6. An explicit request to compile the study session is handled by the StudyReportCompiler (either mode).
        from app.services.research.study_report import is_study_report_request
        if is_study_report_request(turn_create.message):
            await self._execute_study_report_turn(workspace, conversation, turn, raise_on_error=False)
            return self.stream_turn_events(turn.turn_id)

        # 7. Dispatch background execution and return stream generator
        if turn_create.mode == "ground":
            bg_task = asyncio.create_task(
                self._execute_ground_stream_background(
                    workspace_id=workspace.workspace_id,
                    conversation_id=conversation.conversation_id,
                    turn_id=turn.turn_id,
                    user_message=turn_create.message,
                    source_scope=turn_create.source_scope,
                )
            )
            ChatService._running_tasks[turn.turn_id] = bg_task
            bg_task.add_done_callback(lambda t: ChatService._running_tasks.pop(turn.turn_id, None))
            return self.stream_turn_events(turn.turn_id)
        elif turn_create.mode == "research":
            routing_mode, engine = resolve_research_routing(turn_create.research_options)
            admission_controller = self.admission_controller or ResearchAdmissionController(
                quota_service=ResearchQuotaService(self.research_repo),
                rate_limiter=ProviderRateLimiter(self.arq_redis),
                repository=self.research_repo
            )
            base_commit = getattr(workspace, "active_commit_id", None)
            run = await self._admit_research_run_or_close_turn(
                admission_controller,
                turn,
                workspace_id=workspace.workspace_id,
                owner_id=owner_id,
                objective=turn_create.message,
                engine=engine,
                routing_mode=routing_mode,
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

            # NOTE (Gate 3): ARQ background worker is the sole creator of research ChatEvents.
            # Do NOT launch duplicate _bridge_research_events_background task.
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
        user_message: str,
        source_scope: Optional[List[UUID]] = None,
    ):
        """
        Executes a Ground turn in the background with its own DB session (survives client disconnects).
        Every exit path - success, upstream failure, unexpected data, cancellation - closes the turn exactly once
        (compare-and-set on pending/running), so a failed turn can never leave the conversation locked.
        """
        async with async_session_maker() as session:
            event_repo = ChatEventRepository(session)
            event_service = ChatEventService(event_repo, self.arq_redis)
            conv_repo = ConversationRepository(session)

            async def close(status_value: str, error_code: str, message: str, extra_event: Optional[tuple] = None) -> bool:
                try:
                    await session.rollback()
                except Exception:
                    pass
                closed = await conv_repo.set_turn_status(
                    turn_id=turn_id, status=status_value, expected_statuses=["pending", "running"],
                    error_code=error_code, error_message=(message or "")[:2000], completed_at=datetime.now(timezone.utc),
                )
                if closed:
                    if extra_event:
                        await event_service.record_and_publish(turn_id=turn_id, event_type=extra_event[0], payload=extra_event[1])
                    await event_service.record_and_publish(
                        turn_id=turn_id, event_type=EVENT_DONE, payload={"status": status_value, "error": message}
                    )
                return bool(closed)

            try:
                await event_service.record_and_publish(turn_id=turn_id, event_type="status_change", payload={"status": "running"})
                await conv_repo.set_turn_status(turn_id=turn_id, status="running", started_at=datetime.now(timezone.utc))

                # Assemble Ground context adhering strictly to GroundContextPolicy (with the turn's validated scope).
                from app.services.chat.context import build_ground_context
                ground_ctx = await build_ground_context(
                    session=session,
                    workspace_id=workspace_id,
                    conversation_id=conversation_id,
                    query=user_message,
                    explicit_scope=source_scope,
                )

                engine = self.ground_engine or OpenNotebookGroundEngine(
                    workspace_id=workspace_id,
                    client=self.open_notebook_client
                )

                full_answer: List[str] = []
                evidence_refs: List[Any] = []
                evidence_details: List[Any] = []
                unresolved: List[Any] = []
                prov_status: str = "none"

                async for chunk in engine.astream(
                    workspace_id=workspace_id,
                    conversation_id=conversation_id,
                    turn_id=turn_id,
                    query=user_message,
                    db=session,
                    source_scope=ground_ctx.source_scope,
                    ground_context=ground_ctx
                ):
                    if not isinstance(chunk, dict):
                        logger.warning("Ignoring unexpected Ground stream chunk of type %s", type(chunk).__name__)
                        continue
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
                        evidence_details = chunk.get("evidence_details") or evidence_details
                        unresolved = chunk.get("unresolved_citations") or unresolved
                        prov_status = chunk.get("provenance_status") or ev_data.get("provenance_status") or prov_status
                        await event_service.record_and_publish(
                            turn_id,
                            "citation",
                            {"evidence": evidence_details or [e if isinstance(e, dict) else {"source_id": str(e)} for e in evidence_refs],
                             "unresolved_citations": unresolved, "provenance_status": prov_status}
                        )
                    elif ev_type == "done":
                        if not full_answer:
                            ans = chunk.get("answer") or ev_data.get("answer") or ""
                            if ans:
                                full_answer.append(ans)
                        if not evidence_refs:
                            evidence_refs = chunk.get("evidence") or ev_data.get("evidence") or []
                        evidence_details = chunk.get("evidence_details") or evidence_details
                        unresolved = chunk.get("unresolved_citations") or unresolved
                        prov_status = chunk.get("provenance_status") or ev_data.get("provenance_status") or prov_status

                final_answer_text = "".join(full_answer)
                if not final_answer_text.strip():
                    raise HTTPException(status_code=502, detail="ground_upstream_empty_answer")
                formatted_evidence_refs = [e if isinstance(e, dict) else str(e) for e in evidence_refs]

                completed_turn = await conv_repo.set_turn_status(
                    turn_id=turn_id,
                    status="completed",
                    expected_statuses=["pending", "running"],
                    assistant_message=final_answer_text,
                    ground_evidence_refs=formatted_evidence_refs,
                    context_version={"ground_context": ground_ctx.model_dump(mode="json"),
                                     "ground_evidence": {"evidence": evidence_details, "unresolved_citations": unresolved,
                                                         "provenance_status": prov_status}},
                    completed_at=datetime.now(timezone.utc)
                )
                if completed_turn:
                    await event_service.record_and_publish(
                        turn_id=turn_id,
                        event_type=EVENT_DONE,
                        payload={
                            "status": "completed",
                            "assistant_message": final_answer_text,
                            "ground_evidence_refs": formatted_evidence_refs,
                            "evidence_details": evidence_details,
                            "unresolved_citations": unresolved,
                            "provenance_status": prov_status
                        }
                    )
            except asyncio.CancelledError:
                logger.info("Ground turn %s execution was cancelled.", turn_id)
                try:
                    await asyncio.shield(close("cancelled", "turn_cancelled", "Ground turn cancelled",
                                               (EVENT_TURN_CANCELLED, {"status": "cancelled"})))
                except BaseException as close_err:
                    logger.warning("Could not close cancelled Ground turn %s: %s", turn_id, close_err)
                raise
            except HTTPException as e:
                await close("failed", "upstream_ground_failure", str(e.detail), (EVENT_ERROR, {"message": str(e.detail)}))
            except Exception as e:
                logger.error(f"Background ground execution failed: {e}", exc_info=True)
                await close("failed", "ground_execution_error", str(e), (EVENT_ERROR, {"message": str(e)}))

    async def _bridge_research_events_background(
        self,
        turn_id: UUID,
        run_id: UUID
    ):
        """
        Deprecated in Chapter 4 Ticket 02.
        ARQ background worker is the sole authoritative creator of research ChatEvents
        and publisher to Redis turn_events:{turn_id}.
        """
        pass

    async def _recover_stale_active_turn(self, turn: Any) -> bool:
        """
        Close an active turn that provably cannot still be executing, so a crashed request or worker cannot lock the
        conversation forever. Live turns are never touched (the caller keeps returning 409 for them):
          * Ground: no live task in this process and running longer than GROUND_TURN_STALE_AFTER_S (Ground calls are
            bounded by the Open Notebook client timeouts, far below that);
          * Research: its ResearchRun is already terminal (the worker died between run and turn finalization), or no run
            was ever linked and the turn is older than GROUND_TURN_STALE_AFTER_S (admission crashed).
        """
        from app.core.config import settings

        stale_after = int(getattr(settings, "GROUND_TURN_STALE_AFTER_S", 600))
        now = datetime.now(timezone.utc)
        mode = getattr(turn, "mode", None)
        started = getattr(turn, "started_at", None) or getattr(turn, "created_at", None)
        age = (now - started).total_seconds() if isinstance(started, datetime) else None
        new_status, code = None, None
        if mode == "ground":
            task = ChatService._running_tasks.get(turn.turn_id)
            if (task is None or task.done()) and age is not None and age > stale_after:
                new_status, code = "failed", "stale_turn_recovered"
        elif mode == "research":
            run_id = getattr(turn, "research_run_id", None)
            if run_id:
                run = await self.research_repo.get_run(turn.workspace_id, run_id)
                run_status = getattr(run, "status", None)
                if run_status in ("completed", "failed", "partial", "cancelled", "aborted_by_timeline_fence"):
                    new_status = {"aborted_by_timeline_fence": "cancelled", "completed": "failed"}.get(run_status, run_status)
                    code = "turn_reconciled_from_run"
            elif age is not None and age > stale_after:
                new_status, code = "failed", "stale_turn_recovered"
        if not new_status:
            return False
        closed = await self.conv_repo.set_turn_status(
            turn_id=turn.turn_id, status=new_status, expected_statuses=["pending", "running"], error_code=code,
            error_message=f"Recovered a turn that could no longer be executing ({code})", completed_at=now,
        )
        if closed:
            logger.warning("Recovered stale %s turn %s -> %s (%s)", mode, turn.turn_id, new_status, code)
            await self.event_service.record_and_publish(
                turn_id=turn.turn_id, event_type=EVENT_DONE, payload={"status": new_status, "error": code}
            )
        return True

    async def _close_open_turn(self, turn_id: UUID, exc: BaseException) -> None:
        """Close a still-open turn after an unhandled failure or cancellation (no-op if it was already closed)."""
        cancelled = isinstance(exc, asyncio.CancelledError)
        status_value = "cancelled" if cancelled else "failed"
        if cancelled:
            code, message = "turn_cancelled", "Ground turn cancelled"
        elif isinstance(exc, HTTPException):
            code, message = "upstream_ground_failure", str(exc.detail)
        else:
            code, message = "ground_execution_error", str(exc)

        async def _close():
            try:
                await self.db.rollback()
            except Exception:
                pass
            closed = await self.conv_repo.set_turn_status(
                turn_id=turn_id, status=status_value, expected_statuses=["pending", "running"], error_code=code,
                error_message=message[:2000], completed_at=datetime.now(timezone.utc),
            )
            if closed:
                if cancelled:
                    await self.event_service.record_and_publish(turn_id=turn_id, event_type=EVENT_TURN_CANCELLED,
                                                                payload={"status": "cancelled"})
                await self.event_service.record_and_publish(turn_id=turn_id, event_type=EVENT_DONE,
                                                            payload={"status": status_value, "error": message})

        try:
            await asyncio.shield(_close())
        except BaseException as close_err:
            logger.warning("Could not close turn %s after %s: %s", turn_id, type(exc).__name__, close_err)

    async def _execute_ground_turn(
        self,
        workspace: Any,
        conversation: Conversation,
        turn: ConversationTurn,
        stream: bool = False
    ) -> ConversationTurn:
        """Runs a Ground turn; any failure or cancellation (incl. client disconnect) closes the turn exactly once."""
        try:
            return await self._execute_ground_turn_inner(workspace, conversation, turn, stream)
        except BaseException as exc:
            await self._close_open_turn(turn.turn_id, exc)
            raise

    async def _execute_ground_turn_inner(
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
        try:
            ground_ctx = await build_ground_context(
                session=self.db,
                workspace_id=workspace.workspace_id,
                conversation_id=conversation.conversation_id,
                query=turn.user_message,
                explicit_scope=turn.source_scope
            )
        except HTTPException as scope_err:
            # A rejected source scope (e.g. a source of another workspace) must close the turn, otherwise it stays
            # 'running' and blocks the conversation with 409 conversation_turn_in_progress.
            await self.conv_repo.set_turn_status(
                turn_id=turn.turn_id,
                status="failed",
                expected_statuses=["pending", "running"],
                error_code="invalid_source_scope",
                error_message=str(scope_err.detail),
                completed_at=datetime.now(timezone.utc)
            )
            await self.event_service.record_and_publish(
                turn_id=turn.turn_id, event_type="done", payload={"status": "failed", "error": str(scope_err.detail)}
            )
            raise

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
            if not isinstance(state, dict):
                raise HTTPException(status_code=502, detail="ground_upstream_invalid_response")

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
            evidence_details = state.get("evidence_details") or []
            unresolved = state.get("unresolved_citations") or []
            completed_turn = await self.conv_repo.set_turn_status(
                turn_id=turn.turn_id,
                status="completed",
                expected_statuses=["pending", "running"],
                assistant_message=answer,
                ground_evidence_refs=formatted_evidence_refs,
                context_version={"ground_context": ground_ctx.model_dump(mode="json"),
                                 "ground_evidence": {"evidence": evidence_details, "unresolved_citations": unresolved,
                                                     "provenance_status": prov_status}},
                completed_at=datetime.now(timezone.utc)
            )
            if completed_turn:
                await self.event_service.record_and_publish(
                    turn_id=turn.turn_id,
                    event_type="done",
                    payload={
                        "status": "completed",
                        "assistant_message": answer,
                        "ground_evidence_refs": formatted_evidence_refs,
                        "evidence_details": evidence_details,
                        "unresolved_citations": unresolved,
                        "provenance_status": prov_status
                    }
                )
            return completed_turn
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Ground engine run failed: %s", e, exc_info=True)
            await self.conv_repo.set_turn_status(
                turn_id=turn.turn_id,
                status="failed",
                expected_statuses=["pending", "running"],
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

    async def _execute_study_report_turn(
        self,
        workspace: Any,
        conversation: Conversation,
        turn: ConversationTurn,
        raise_on_error: bool = True,
    ) -> Optional[ConversationTurn]:
        """
        Compile the conversation into a cited study-session paper (explicit request only). No research is run: the
        compiler reads this conversation's turns, cited workspace sources, research evidence and scratchpad notes.
        """
        from app.schemas.chat import EVENT_TURN_COMPLETED, EVENT_TURN_FAILED
        from app.services.research.study_report import StudyReportCompiler, StudySessionEmpty

        await self.conv_repo.set_turn_status(turn_id=turn.turn_id, status="running", started_at=datetime.now(timezone.utc))
        await self.event_service.record_and_publish(
            turn_id=turn.turn_id, event_type=EVENT_STATUS_CHANGE, payload={"status": "running", "task": "study_report"}
        )
        try:
            result = await StudyReportCompiler(self.db, llm=getattr(self, "study_report_llm", None)).compile(
                workspace_id=workspace.workspace_id, conversation_id=conversation.conversation_id, request=turn.user_message,
                owner_id=turn.owner_id,
            )
        except Exception as exc:
            code = "study_session_empty" if isinstance(exc, StudySessionEmpty) else "study_report_failed"
            logger.error("Study report compilation failed for conversation %s: %s", conversation.conversation_id, exc)
            await self.db.rollback()
            await self.conv_repo.set_turn_status(
                turn_id=turn.turn_id, status="failed", expected_statuses=["pending", "running"], error_code=code,
                error_message=str(exc), completed_at=datetime.now(timezone.utc)
            )
            payload = {"status": "failed", "error": code}
            await self.event_service.record_and_publish(turn_id=turn.turn_id, event_type=EVENT_TURN_FAILED, payload=payload)
            await self.event_service.record_and_publish(turn_id=turn.turn_id, event_type=EVENT_DONE, payload=payload)
            if raise_on_error:
                raise HTTPException(status_code=422 if code == "study_session_empty" else 500, detail=code)
            return None

        study = {k: result[k] for k in ("report_id", "candidate_id", "warnings", "cited")}
        completed = await self.conv_repo.set_turn_status(
            turn_id=turn.turn_id, status="completed", expected_statuses=["pending", "running"],
            assistant_message=result["content"], context_version={"study_report": {k: study[k] for k in ("report_id", "candidate_id")}},
            completed_at=datetime.now(timezone.utc)
        )
        payload = {"status": "completed", "assistant_message": result["content"], "study_report": study}
        await self.event_service.record_and_publish(turn_id=turn.turn_id, event_type=EVENT_TURN_COMPLETED, payload=payload)
        await self.event_service.record_and_publish(turn_id=turn.turn_id, event_type=EVENT_DONE, payload=payload)
        return completed

    async def _admit_research_run_or_close_turn(self, admission_controller: Any, turn: ConversationTurn, **admit_kwargs: Any):
        """
        Admit a research run. If admission rejects it (unsupported engine, quota, rate limit) the turn row
        already exists, so close it as failed before re-raising; otherwise it stays pending and blocks the
        conversation with 409 conversation_turn_in_progress.
        """
        try:
            return await admission_controller.admit_research_run(**admit_kwargs)
        except HTTPException as admission_err:
            await self.conv_repo.set_turn_status(
                turn_id=turn.turn_id,
                status="failed",
                expected_statuses=["pending"],
                error_code=str(admission_err.detail),
                error_message=str(admission_err.detail),
                completed_at=datetime.now(timezone.utc)
            )
            raise

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
        routing_mode, engine = resolve_research_routing(turn_create.research_options if turn_create else None)
        engine_revision = (turn_create.research_options or {}).get("engine_revision") if turn_create else None

        admission_controller = self.admission_controller or ResearchAdmissionController(
            quota_service=ResearchQuotaService(self.research_repo),
            rate_limiter=ProviderRateLimiter(self.arq_redis),
            repository=self.research_repo
        )

        # 1. Admit Research Run
        base_commit = getattr(workspace, "active_commit_id", None)
        run = await self._admit_research_run_or_close_turn(
            admission_controller,
            turn,
            workspace_id=workspace.workspace_id,
            owner_id=turn.owner_id,
            objective=turn.user_message,
            engine=engine,
            routing_mode=routing_mode,
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

        # 3. Update ConversationTurn status to cancelled via atomic CAS
        cancelled_turn = await self.conv_repo.set_turn_status(
            turn_id=turn_id,
            status="cancelled",
            expected_statuses=["pending", "running"],
            completed_at=datetime.now(timezone.utc)
        )
        if not cancelled_turn:
            current_turn = await self.conv_repo.get_turn(workspace_id, conversation_id, turn_id)
            if current_turn and current_turn.status == "cancelled":
                return current_turn
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel turn with status '{current_turn.status if current_turn else 'terminal'}'"
            )

        # 4. Synchronously record and publish turn.cancelled and done
        await self.event_service.record_and_publish(
            turn_id=turn_id,
            event_type=EVENT_TURN_CANCELLED,
            payload={"status": "cancelled", "reason": "Cancelled by user"}
        )
        await self.event_service.record_and_publish(
            turn_id=turn_id,
            event_type=EVENT_DONE,
            payload={"status": "cancelled", "reason": "Cancelled by user"}
        )

        return cancelled_turn
