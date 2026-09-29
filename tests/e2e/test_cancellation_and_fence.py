"""
End-to-End Tests: Turn Cancellation, Cooperative Worker Cancellation,
and Concurrency Timeline Epoch Fencing.

Tests covered:
1. Ground in-flight task cancellation: initiates cancellation on in-flight ground turn,
   verifies underlying asyncio task is cancelled and turn.cancelled event emitted.
2. Research in-flight cancellation via Redis pub/sub: initiates cancellation on research
   turn, verifies cancellation signal published to research_cancellation:{run_id} and
   lifecycle status transitions to cancelled.
3. Concurrency fence (Worker timeline epoch check): stale worker detects epoch mismatch
   (e.g., from rollback), aborts execution, transitions run and turn to cancelled,
   and does not mutate workspace state.
4. Cancellation idempotency: double-cancel returns cancelled turn without error or duplicate events.
5. Terminal state guard: canceling an already completed or failed turn raises HTTP 400.
"""

import asyncio
import json
import pytest
from datetime import datetime, timezone
from uuid import uuid4, UUID
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException, status

from app.models.conversation import Conversation, ConversationTurn
from app.models.workspace import Workspace
from app.models.research import ResearchRun
from app.services.chat.service import ChatService
from app.workers.tasks import run_research_agent_job


@pytest.mark.asyncio
async def test_ground_turn_in_flight_cancellation():
    """
    E2E Test: Ground in-flight task cancellation.
    Submitting a Ground turn spawns a background asyncio task.
    Calling cancel_turn cancels the active task, updates turn status to 'cancelled',
    and publishes 'turn.cancelled' and 'done' events.
    """
    workspace_id = uuid4()
    conversation_id = uuid4()
    turn_id = uuid4()
    owner_id = uuid4()

    mock_db = AsyncMock()
    mock_conv_repo = AsyncMock()
    mock_workspace_repo = AsyncMock()
    mock_research_repo = AsyncMock()
    mock_arq = AsyncMock()

    mock_ws = Workspace(workspace_id=workspace_id, owner_id=owner_id, timeline_epoch=1)
    mock_conv = Conversation(
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        owner_id=owner_id,
        status="active"
    )
    mock_turn = ConversationTurn(
        turn_id=turn_id,
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        owner_id=owner_id,
        sequence=1,
        mode="ground",
        user_message="Explain thermodynamics",
        status="running",
        ground_evidence_refs=[],
        context_version={},
        created_at=datetime.now(timezone.utc)
    )

    mock_workspace_repo.get_workspace.return_value = mock_ws
    mock_conv_repo.get_conversation.return_value = mock_conv
    mock_conv_repo.get_turn.return_value = mock_turn

    cancelled_turn = ConversationTurn(
        turn_id=turn_id,
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        owner_id=owner_id,
        sequence=1,
        mode="ground",
        user_message="Explain thermodynamics",
        status="cancelled",
        ground_evidence_refs=[],
        context_version={},
        created_at=datetime.now(timezone.utc)
    )
    mock_conv_repo.set_turn_status.return_value = cancelled_turn

    # Launch a simulated long-running background task
    task_cancelled_event = asyncio.Event()

    async def long_running_ground_task():
        try:
            await asyncio.sleep(100)
        except asyncio.CancelledError:
            task_cancelled_event.set()
            raise

    ground_task = asyncio.create_task(long_running_ground_task())
    ChatService._running_tasks[turn_id] = ground_task
    # Yield control to allow background task to start executing
    await asyncio.sleep(0)

    service = ChatService(
        db=mock_db,
        conv_repo=mock_conv_repo,
        workspace_repo=mock_workspace_repo,
        research_repo=mock_research_repo,
        arq_redis=mock_arq
    )
    service.event_service = AsyncMock()

    # Cancel the turn
    result = await service.cancel_turn(workspace_id, conversation_id, turn_id, owner_id)

    # 1. Background task must be cancelled
    with pytest.raises(asyncio.CancelledError):
        await ground_task
    assert ground_task.cancelled()
    assert task_cancelled_event.is_set()
    assert turn_id not in ChatService._running_tasks

    # 2. Turn status must be cancelled
    assert result.status == "cancelled"
    mock_conv_repo.set_turn_status.assert_awaited_once()
    assert mock_conv_repo.set_turn_status.call_args[1]["status"] == "cancelled"

    # 3. Synchronous turn.cancelled and done events must be recorded and published
    published_events = [call[1]["event_type"] for call in service.event_service.record_and_publish.call_args_list]
    assert "turn.cancelled" in published_events
    assert "done" in published_events


@pytest.mark.asyncio
async def test_research_turn_in_flight_cancellation_pubsub():
    """
    E2E Test: Research in-flight cancellation via Redis pub/sub.
    Initiating cancellation on a research turn transitions the ResearchRun to 'cancelled'
    and publishes cooperative cancellation messages to Redis on research_cancellation:{run_id}
    and research_events:{run_id}.
    """
    workspace_id = uuid4()
    conversation_id = uuid4()
    turn_id = uuid4()
    run_id = uuid4()
    owner_id = uuid4()

    mock_db = AsyncMock()
    mock_conv_repo = AsyncMock()
    mock_workspace_repo = AsyncMock()
    mock_research_repo = AsyncMock()
    mock_arq = AsyncMock()

    mock_ws = Workspace(workspace_id=workspace_id, owner_id=owner_id, timeline_epoch=1)
    mock_conv = Conversation(
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        owner_id=owner_id,
        status="active"
    )
    mock_turn = ConversationTurn(
        turn_id=turn_id,
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        owner_id=owner_id,
        sequence=1,
        mode="research",
        research_run_id=run_id,
        user_message="Deep research on graphene superconductors",
        status="running",
        ground_evidence_refs=[],
        context_version={},
        created_at=datetime.now(timezone.utc)
    )
    mock_run = ResearchRun(
        run_id=run_id,
        workspace_id=workspace_id,
        turn_id=turn_id,
        objective="Deep research on graphene superconductors",
        status="running",
        created_at=datetime.now(timezone.utc)
    )

    mock_workspace_repo.get_workspace.return_value = mock_ws
    mock_conv_repo.get_conversation.return_value = mock_conv
    mock_conv_repo.get_turn.return_value = mock_turn
    mock_research_repo.get_run.return_value = mock_run

    cancelled_turn = ConversationTurn(
        turn_id=turn_id,
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        owner_id=owner_id,
        sequence=1,
        mode="research",
        research_run_id=run_id,
        user_message="Deep research on graphene superconductors",
        status="cancelled",
        ground_evidence_refs=[],
        context_version={},
        created_at=datetime.now(timezone.utc)
    )
    mock_conv_repo.set_turn_status.return_value = cancelled_turn

    service = ChatService(
        db=mock_db,
        conv_repo=mock_conv_repo,
        workspace_repo=mock_workspace_repo,
        research_repo=mock_research_repo,
        arq_redis=mock_arq
    )
    service.event_service = AsyncMock()

    with patch("app.services.research.lifecycle.ResearchLifecycleService.transition_run", new_callable=AsyncMock) as mock_transition:
        result = await service.cancel_turn(workspace_id, conversation_id, turn_id, owner_id)

        # 1. Lifecycle transition to cancelled
        mock_transition.assert_awaited_once_with(
            workspace_id=workspace_id,
            run_id=run_id,
            target_status="cancelled",
            metadata={"reason": "Cancelled by user via turn cancellation endpoint"}
        )

        # 2. Redis cancellation published
        pub_calls = mock_arq.publish.call_args_list
        channels = [call[0][0] for call in pub_calls]
        assert f"research_cancellation:{run_id}" in channels
        assert f"research_events:{run_id}" in channels

        cancel_payload = json.loads(pub_calls[0][0][1])
        assert cancel_payload["event_type"] == "cancelled"
        assert cancel_payload["status"] == "cancelled"
        assert cancel_payload["run_id"] == str(run_id)

        # 3. Turn status and events
        assert result.status == "cancelled"
        published_events = [call[1]["event_type"] for call in service.event_service.record_and_publish.call_args_list]
        assert "turn.cancelled" in published_events
        assert "done" in published_events


@pytest.mark.asyncio
async def test_worker_timeline_epoch_fence_aborts_stale_research_run():
    """
    E2E Test: Worker timeline epoch fence.
    When a workspace is rolled back while a research worker is executing,
    the workspace timeline_epoch is incremented.
    When the worker checks timeline_epoch before state finalization, it discovers
    expected_epoch != current_epoch, immediately aborts, transitions run and turn
    to cancelled, emits timeline_fence_aborted error code, and does not mutate graph state.
    """
    workspace_id = uuid4()
    run_id = uuid4()
    turn_id = uuid4()

    mock_ws_start = Workspace(
        workspace_id=workspace_id,
        owner_id=uuid4(),
        timeline_epoch=1
    )
    mock_ws_rolled_back = Workspace(
        workspace_id=workspace_id,
        owner_id=uuid4(),
        timeline_epoch=2  # Advanced due to rollback!
    )
    mock_run = ResearchRun(
        run_id=run_id,
        workspace_id=workspace_id,
        turn_id=turn_id,
        objective="Analyze neural network scaling laws",
        status="running"
    )

    mock_redis = AsyncMock()
    ctx = {
        "job_id": "test_fence_job_1",
        "redis": mock_redis,
        "llm_call": AsyncMock(return_value="Lightweight summary")
    }

    async def mock_stream_events(*args, **kwargs):
        yield {"status": "planning", "message": "Planning research"}
        yield {"status": "researching", "message": "Searching web"}
        yield {"status": "synthesizing", "message": "Synthesizing report"}

    mock_engine = MagicMock()
    mock_engine.astream_events = mock_stream_events

    with patch("app.workers.tasks.async_session_maker") as mock_session_cls, \
         patch("app.integrations.research_engine.factory.ResearchEngineFactory.get_engine", return_value=mock_engine), \
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

        # 1. First session query: workspace (epoch 1), run
        res_ws_1 = MagicMock()
        res_ws_1.scalars.return_value.first.return_value = mock_ws_start
        res_run_1 = MagicMock()
        res_run_1.scalars.return_value.first.return_value = mock_run

        # 2. Concurrency check query: workspace current (epoch 2)
        res_ws_2 = MagicMock()
        res_ws_2.scalars.return_value.first.return_value = mock_ws_rolled_back

        mock_session.execute = AsyncMock(side_effect=[res_ws_1, res_run_1, res_ws_2])

        result = await run_research_agent_job(
            ctx,
            workspace_id=str(workspace_id),
            objective="Analyze neural network scaling laws",
            run_id=str(run_id)
        )

        # 1. Worker returns aborted_by_timeline_fence status
        assert result["status"] == "aborted_by_timeline_fence"
        assert "timeline fence" in result["reason"].lower()

        # 2. Run lifecycle transitioned to aborted_by_timeline_fence
        mock_lifecycle.transition_run.assert_awaited_once()
        assert mock_lifecycle.transition_run.await_args[0][2] == "aborted_by_timeline_fence"

        # 3. Turn status set to cancelled with error_code timeline_fence_aborted
        mock_conv_repo.set_turn_status.assert_awaited_once()
        conv_call_kwargs = mock_conv_repo.set_turn_status.await_args[1]
        assert conv_call_kwargs["status"] == "cancelled"
        assert conv_call_kwargs["error_code"] == "timeline_fence_aborted"
        assert "timeline fence" in conv_call_kwargs["error_message"].lower()

        # 4. Chat events bridged for cancellation
        bridge_event_types = [call[0][1] for call in mock_event_service.record_and_publish.call_args_list]
        assert "turn.cancelled" in bridge_event_types
        assert "done" in bridge_event_types

        # 5. Redis fence event published
        fence_calls = [
            json.loads(args[1]) for args, _ in mock_redis.publish.call_args_list
            if "workspace.rollback.fence_triggered" in args[1]
        ]
        assert len(fence_calls) > 0
        fence_ev = fence_calls[0]
        assert fence_ev["event_type"] == "workspace.rollback.fence_triggered"
        assert fence_ev["expected_epoch"] == 1
        assert fence_ev["current_epoch"] == 2


@pytest.mark.asyncio
async def test_cancellation_idempotency_double_cancel():
    """
    E2E Test: Cancelling an already cancelled turn is idempotent.
    Returns the cancelled turn immediately without raising an error or duplicating events.
    """
    workspace_id = uuid4()
    conversation_id = uuid4()
    turn_id = uuid4()
    owner_id = uuid4()

    mock_db = AsyncMock()
    mock_conv_repo = AsyncMock()
    mock_workspace_repo = AsyncMock()
    mock_research_repo = AsyncMock()
    mock_arq = AsyncMock()

    mock_ws = Workspace(workspace_id=workspace_id, owner_id=owner_id, timeline_epoch=1)
    mock_conv = Conversation(
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        owner_id=owner_id,
        status="active"
    )
    already_cancelled_turn = ConversationTurn(
        turn_id=turn_id,
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        owner_id=owner_id,
        sequence=1,
        mode="ground",
        user_message="Test query",
        status="cancelled",
        ground_evidence_refs=[],
        context_version={},
        created_at=datetime.now(timezone.utc)
    )

    mock_workspace_repo.get_workspace.return_value = mock_ws
    mock_conv_repo.get_conversation.return_value = mock_conv
    mock_conv_repo.get_turn.return_value = already_cancelled_turn

    service = ChatService(
        db=mock_db,
        conv_repo=mock_conv_repo,
        workspace_repo=mock_workspace_repo,
        research_repo=mock_research_repo,
        arq_redis=mock_arq
    )
    service.event_service = AsyncMock()

    result = await service.cancel_turn(workspace_id, conversation_id, turn_id, owner_id)

    assert result.status == "cancelled"
    # Must NOT call set_turn_status or record_and_publish again
    mock_conv_repo.set_turn_status.assert_not_called()
    service.event_service.record_and_publish.assert_not_called()


@pytest.mark.asyncio
async def test_cancellation_terminal_state_guard():
    """
    E2E Test: Cancelling an already completed or failed turn is rejected with HTTP 400.
    """
    workspace_id = uuid4()
    conversation_id = uuid4()
    turn_id = uuid4()
    owner_id = uuid4()

    mock_db = AsyncMock()
    mock_conv_repo = AsyncMock()
    mock_workspace_repo = AsyncMock()
    mock_research_repo = AsyncMock()
    mock_arq = AsyncMock()

    mock_ws = Workspace(workspace_id=workspace_id, owner_id=owner_id, timeline_epoch=1)
    mock_conv = Conversation(
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        owner_id=owner_id,
        status="active"
    )
    completed_turn = ConversationTurn(
        turn_id=turn_id,
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        owner_id=owner_id,
        sequence=1,
        mode="ground",
        user_message="Test query",
        status="completed",
        ground_evidence_refs=[],
        context_version={},
        created_at=datetime.now(timezone.utc)
    )

    mock_workspace_repo.get_workspace.return_value = mock_ws
    mock_conv_repo.get_conversation.return_value = mock_conv
    mock_conv_repo.get_turn.return_value = completed_turn

    service = ChatService(
        db=mock_db,
        conv_repo=mock_conv_repo,
        workspace_repo=mock_workspace_repo,
        research_repo=mock_research_repo,
        arq_redis=mock_arq
    )

    # 1. Completed turn rejection
    with pytest.raises(HTTPException) as exc_info:
        await service.cancel_turn(workspace_id, conversation_id, turn_id, owner_id)
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "Cannot cancel turn with status 'completed'" in exc_info.value.detail

    # 2. Failed turn rejection
    failed_turn = ConversationTurn(
        turn_id=turn_id,
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        owner_id=owner_id,
        sequence=1,
        mode="ground",
        user_message="Test query",
        status="failed",
        ground_evidence_refs=[],
        context_version={},
        created_at=datetime.now(timezone.utc)
    )
    mock_conv_repo.get_turn.return_value = failed_turn

    with pytest.raises(HTTPException) as exc_info_failed:
        await service.cancel_turn(workspace_id, conversation_id, turn_id, owner_id)
    assert exc_info_failed.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "Cannot cancel turn with status 'failed'" in exc_info_failed.value.detail
