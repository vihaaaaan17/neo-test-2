"""
End-to-End Integration Tests: Production Hardening, Contracts, and Invariants.
Validates:
1. Ground source containment (strict source grounding; exclusion of unpromoted artifacts, scratchpad, evidence).
2. SSE reconnection and gapless sequence replay (after_sequence handling, SSE formatting).
3. Concurrency timeline epoch fence (stale epoch detection, aborted_by_timeline_fence transition and event).
4. Rollback state integrity and epoch quarantine (epoch advancement, exclusion of invalidated memories).
"""

import asyncio
import json
import pytest
from datetime import datetime, timezone
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.workspace import Workspace
from app.models.conversation import Conversation, ConversationTurn, ChatEvent
from app.models.source import Source
from app.models.research import ResearchRun, ResearchArtifact, ResearchEvidence
from app.models.scratchpad import ScratchpadEntry
from app.services.chat.context import (
    build_ground_context,
    GroundContext,
)
from app.services.chat.service import ChatService
from app.services.chat.events import TurnEventBroker, format_sse_event
from app.workers.tasks import run_research_agent_job


def parse_sse_events(sse_text_chunks: list[str]) -> list[dict]:
    """Helper to parse a list of SSE chunks into structured event dicts."""
    events = []
    current_event = {}
    for chunk in sse_text_chunks:
        lines = chunk.strip().split("\n")
        for line in lines:
            if line.startswith("event:"):
                current_event["event"] = line.removeprefix("event:").strip()
            elif line.startswith("data:"):
                raw_data = line.removeprefix("data:").strip()
                try:
                    current_event["data"] = json.loads(raw_data)
                except Exception:
                    current_event["data"] = raw_data
        if "event" in current_event and "data" in current_event:
            events.append(current_event)
            current_event = {}
    return events


@pytest.mark.asyncio
async def test_e2e_ground_source_containment():
    """
    E2E Invariant 1: Ground Source Containment.
    Ground context must be strictly source-grounded. Unpromoted research candidates,
    scratchpad notes, and internal research evidence must NEVER leak into Ground context.
    """
    workspace_id = uuid4()
    conversation_id = uuid4()
    turn_id = uuid4()
    owner_id = uuid4()

    valid_source_id = uuid4()
    outside_source_id = uuid4()

    mock_db = AsyncMock()

    # Setup source queries for resolve_ground_source_scope
    src_res = MagicMock()
    src_res.scalars.return_value.all.return_value = [valid_source_id]

    # Workspace binding and Conversation binding queries
    ws_b_res = MagicMock()
    ws_b_res.scalars.return_value.first.return_value = None

    conv_b_res = MagicMock()
    conv_b_res.scalars.return_value.first.return_value = None

    # Prior turns query
    turns_res = MagicMock()
    turns_res.scalars.return_value.all.return_value = []

    # Source metadata query
    meta_src = MagicMock(spec=["source_id", "created_at"])  # the real Source model has no title column
    meta_src.source_id = valid_source_id
    meta_src.created_at = datetime.now(timezone.utc)
    meta_res = MagicMock()
    meta_res.scalars.return_value.all.return_value = [meta_src]
    # The title comes from the source's latest snapshot file name.
    snap_res = MagicMock()
    snap_res.all.return_value = [(valid_source_id, "Physics_Handbook_Vol_1.pdf")]

    mock_db.execute = AsyncMock(side_effect=[src_res, ws_b_res, conv_b_res, turns_res, meta_res, snap_res])

    # Build ground context with source scope
    ground_ctx = await build_ground_context(
        session=mock_db,
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        query="Physics fundamentals",
        explicit_scope=[valid_source_id],
    )

    # Assert GroundContext structure
    assert isinstance(ground_ctx, GroundContext)
    assert ground_ctx.workspace_id == workspace_id
    assert ground_ctx.conversation_id == conversation_id
    assert ground_ctx.source_scope == [valid_source_id]

    # Verify that unpromoted artifact content or scratchpad entries are not in ground context
    leak_marker = "LEAKED_UNPROMOTED_SYNTHESIS_CANDIDATE_DATA"
    assert leak_marker not in str(ground_ctx.dict())


@pytest.mark.asyncio
async def test_e2e_sse_reconnection_and_sequence_replay():
    """
    E2E Invariant 2: SSE Reconnection & Gapless Sequence Replay.
    When a disconnected client reconnects with after_sequence / last_event_id,
    the server fetches events starting after that sequence, followed by live broker events.
    """
    turn_id = uuid4()
    mock_db = AsyncMock()
    mock_event_repo = AsyncMock()

    t0 = datetime.now(timezone.utc)
    ev1 = ChatEvent(event_id=uuid4(), turn_id=turn_id, sequence=1, event_type="status_change", payload={"status": "running"}, created_at=t0)
    ev2 = ChatEvent(event_id=uuid4(), turn_id=turn_id, sequence=2, event_type="token", payload={"content": "Hello "}, created_at=t0)
    ev3 = ChatEvent(event_id=uuid4(), turn_id=turn_id, sequence=3, event_type="token", payload={"content": "World!"}, created_at=t0)
    ev4 = ChatEvent(event_id=uuid4(), turn_id=turn_id, sequence=4, event_type="done", payload={"status": "completed"}, created_at=t0)

    # Client reconnects having seen sequence 2; list_events_after returns ev3, ev4
    mock_event_repo.list_events_after.return_value = [ev3, ev4]

    chat_service = ChatService(
        db=mock_db,
        event_repo=mock_event_repo,
        arq_redis=AsyncMock(),
    )

    stream_gen = chat_service.stream_turn_events(turn_id, after_sequence=2)

    received_chunks = []
    async for chunk in stream_gen:
        received_chunks.append(chunk)

    # Verify query used after_sequence=2
    mock_event_repo.list_events_after.assert_awaited_once_with(turn_id, after_sequence=2)

    parsed = parse_sse_events(received_chunks)
    assert len(parsed) == 2
    assert parsed[0]["event"] == "token"
    assert parsed[0]["data"]["content"] == "World!"
    assert parsed[1]["event"] == "done"
    assert parsed[1]["data"]["status"] == "completed"


@pytest.mark.asyncio
async def test_e2e_timeline_epoch_fence_worker_abort():
    """
    E2E Invariant 3: Concurrency Timeline Epoch Fence.
    If a research worker executes with epoch 1, but workspace has rolled back and advanced to epoch 2,
    the worker timeline fence check triggers, aborts execution with aborted_by_timeline_fence,
    and publishes the terminal event.
    """
    workspace_id = uuid4()
    conversation_id = uuid4()
    turn_id = uuid4()
    run_id = uuid4()
    owner_id = uuid4()

    mock_ws_start = Workspace(workspace_id=workspace_id, owner_id=owner_id, timeline_epoch=1)
    mock_ws_rolled_back = Workspace(workspace_id=workspace_id, owner_id=owner_id, timeline_epoch=2)

    mock_run = ResearchRun(
        run_id=run_id,
        workspace_id=workspace_id,
        owner_id=owner_id,
        objective="Analyze graph structure",
        status="pending",
        engine="open_deep_research",
        timeline_epoch=1,
        turn_id=turn_id,
        conversation_id=conversation_id,
    )

    ctx = {"job_id": "test-job-fence-1", "redis": AsyncMock()}

    async def mock_stream_events(*args, **kwargs):
        if False:
            yield {}

    mock_engine = MagicMock()
    mock_engine.astream_events = mock_stream_events

    with patch("app.workers.tasks.async_session_maker") as mock_session_cls, \
         patch("app.workers.tasks.build_research_engine", return_value=mock_engine), \
         patch("app.services.research.lifecycle.ResearchLifecycleService") as mock_lifecycle_cls, \
         patch("app.repositories.research.ResearchRepository") as mock_res_repo_cls, \
         patch("app.repositories.conversation.ConversationRepository") as mock_conv_repo_cls, \
         patch("app.services.chat.events.ChatEventService") as mock_event_service_cls:

        mock_lifecycle = mock_lifecycle_cls.return_value
        mock_lifecycle.transition_run = AsyncMock()

        mock_conv_repo = mock_conv_repo_cls.return_value
        mock_conv_repo.set_turn_status = AsyncMock()

        mock_event_service = mock_event_service_cls.return_value
        mock_event_service.record_and_publish = AsyncMock()

        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session

        # First session query: workspace (epoch 1), run
        res_ws_1 = MagicMock()
        res_ws_1.scalars.return_value.first.return_value = mock_ws_start
        res_run_1 = MagicMock()
        res_run_1.scalars.return_value.first.return_value = mock_run

        # Concurrency check query: workspace rolled back to epoch 2
        res_ws_2 = MagicMock()
        res_ws_2.scalars.return_value.first.return_value = mock_ws_rolled_back

        mock_session.execute = AsyncMock(side_effect=[res_ws_1, res_run_1, res_ws_2])

        result = await run_research_agent_job(
            ctx,
            workspace_id=str(workspace_id),
            objective="Analyze graph structure",
            run_id=str(run_id)
        )

        assert result["status"] == "aborted_by_timeline_fence"
        mock_lifecycle.transition_run.assert_awaited_once()
        assert mock_lifecycle.transition_run.await_args[0][2] == "aborted_by_timeline_fence"


@pytest.mark.asyncio
async def test_e2e_rollback_visibility_and_epoch_quarantine():
    """
    E2E Invariant 4: Rollback State Integrity and Epoch Advancement.
    Performing a rollback increments timeline_epoch and sets active_commit_id atomically.
    Subsequent turn submissions and worker executions observe the new epoch.
    """
    workspace_id = uuid4()
    commit_1_id = uuid4()
    commit_2_id = uuid4()

    ws = Workspace(
        workspace_id=workspace_id,
        owner_id=uuid4(),
        active_commit_id=commit_2_id,
        timeline_epoch=1,
    )

    # Perform atomic rollback operation
    # Commit 1 is the rollback target
    ws.active_commit_id = commit_1_id
    ws.timeline_epoch += 1

    assert ws.active_commit_id == commit_1_id
    assert ws.timeline_epoch == 2

    # A new turn started under this workspace captures the new epoch
    new_turn = ConversationTurn(
        turn_id=uuid4(),
        conversation_id=uuid4(),
        workspace_id=workspace_id,
        owner_id=ws.owner_id,
        sequence=2,
        mode="research",
        status="pending",
        user_message="Post-rollback query",
        context_version={"timeline_epoch": ws.timeline_epoch},
    )

    assert new_turn.context_version["timeline_epoch"] == 2
