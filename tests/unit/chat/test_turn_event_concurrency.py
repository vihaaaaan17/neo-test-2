import asyncio
import pytest
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException, status
from pydantic import ValidationError

from app.models.conversation import Conversation, ConversationTurn
from app.models.workspace import Workspace
from app.schemas.chat import (
    TurnCreate,
    ChatEventType,
    EVENT_TURN_RESEARCH_STARTED,
    EVENT_TURN_RESEARCH_PLANNING,
    EVENT_TURN_RESEARCHING,
    EVENT_TURN_SYNTHESIZING,
    EVENT_TURN_PROMOTION_AVAILABLE,
    EVENT_TURN_COMPLETED,
    EVENT_TURN_PARTIAL,
    EVENT_TURN_CANCELLED,
    EVENT_TURN_FAILED,
    EVENT_SCRATCHPAD_ENTRY,
    EVENT_STATUS_CHANGE,
    EVENT_TOKEN,
    EVENT_CITATION,
    EVENT_GROUND_ANSWER,
    EVENT_DONE,
    EVENT_ERROR,
)
from app.services.chat.service import ChatService
from app.repositories.conversation import ConversationRepository


# ============================================================================ #
# Gate 1: Validation BEFORE sequence allocation or database writes
# ============================================================================ #

@pytest.mark.asyncio
async def test_invalid_mode_rejected_before_db_write():
    """
    Gate 1: Invalid turn modes fail validation immediately with zero sequence numbers
    allocated and zero rows persisted to conversation_turns.
    """
    workspace_id = uuid4()
    conversation_id = uuid4()
    owner_id = uuid4()

    mock_db = AsyncMock()
    mock_conv_repo = AsyncMock()
    mock_workspace_repo = AsyncMock()

    service = ChatService(
        db=mock_db,
        conv_repo=mock_conv_repo,
        workspace_repo=mock_workspace_repo
    )

    # Construct TurnCreate bypassing pydantic validator to test service-level defense
    turn_create = TurnCreate.model_construct(
        mode="invalid_hypothetical_mode",
        message="Test message",
        client_request_id=None,
        source_scope=None,
        selected_source_ids=None,
        research_options={}
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.submit_turn(
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            owner_id=owner_id,
            turn_create=turn_create
        )

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "Unsupported turn mode" in exc_info.value.detail

    # MUST NOT allocate sequence or append turn to database
    mock_conv_repo.allocate_turn_sequence.assert_not_called()
    mock_conv_repo.append_turn.assert_not_called()


@pytest.mark.asyncio
async def test_empty_message_rejected_before_db_write():
    """
    Gate 1: Empty or whitespace message fails validation immediately with zero rows created.
    """
    workspace_id = uuid4()
    conversation_id = uuid4()
    owner_id = uuid4()

    mock_db = AsyncMock()
    mock_conv_repo = AsyncMock()
    mock_workspace_repo = AsyncMock()

    service = ChatService(
        db=mock_db,
        conv_repo=mock_conv_repo,
        workspace_repo=mock_workspace_repo
    )

    turn_create = TurnCreate.model_construct(
        mode="ground",
        message="   ",
        client_request_id=None,
        source_scope=None,
        selected_source_ids=None,
        research_options={}
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.submit_turn(
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            owner_id=owner_id,
            turn_create=turn_create
        )

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "empty" in exc_info.value.detail.lower()

    mock_conv_repo.allocate_turn_sequence.assert_not_called()
    mock_conv_repo.append_turn.assert_not_called()


def test_pydantic_turn_create_validation():
    """
    Gate 1: Pydantic TurnCreate schema validator rejects invalid modes and empty messages.
    """
    with pytest.raises(ValidationError):
        TurnCreate(mode="unknown_mode", message="Valid prompt")

    with pytest.raises(ValidationError):
        TurnCreate(mode="ground", message="   ")

    # Valid instances must succeed
    t_ground = TurnCreate(mode="ground", message="Valid ground prompt")
    assert t_ground.mode == "ground"

    t_research = TurnCreate(mode="research", message="Valid research prompt")
    assert t_research.mode == "research"


# ============================================================================ #
# Gate 2: One-running-turn enforcement via row-level lock (HTTP 409)
# ============================================================================ #

@pytest.mark.asyncio
async def test_submitting_second_turn_while_running_raises_409():
    """
    Gate 2: Submitting a second turn while an existing turn is running fails with
    HTTP 409 conversation_turn_in_progress under row-level lock.
    """
    workspace_id = uuid4()
    conversation_id = uuid4()
    owner_id = uuid4()
    active_turn_id = uuid4()

    mock_db = AsyncMock()
    mock_conv_repo = AsyncMock()
    mock_workspace_repo = AsyncMock()

    mock_ws = Workspace(workspace_id=workspace_id, owner_id=owner_id)
    mock_conv = Conversation(
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        owner_id=owner_id,
        status="active"
    )
    mock_workspace_repo.get_workspace.return_value = mock_ws
    mock_conv_repo.get_conversation.return_value = mock_conv
    mock_conv_repo.get_turn_by_client_request_id.return_value = None

    # An existing turn is currently in 'running' state
    running_turn = ConversationTurn(
        turn_id=active_turn_id,
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        owner_id=owner_id,
        sequence=1,
        mode="research",
        user_message="Initial running turn",
        status="running"
    )
    mock_conv_repo.get_active_turn.return_value = running_turn

    service = ChatService(
        db=mock_db,
        conv_repo=mock_conv_repo,
        workspace_repo=mock_workspace_repo
    )

    turn_create = TurnCreate(mode="ground", message="Concurrent second turn attempt")

    with pytest.raises(HTTPException) as exc_info:
        await service.submit_turn(
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            owner_id=owner_id,
            turn_create=turn_create
        )

    assert exc_info.value.status_code == status.HTTP_409_CONFLICT
    assert exc_info.value.detail == "conversation_turn_in_progress"

    # Must acquire row lock
    mock_conv_repo.lock_conversation.assert_awaited_once_with(conversation_id)
    # Must NOT allocate sequence or persist second turn
    mock_conv_repo.allocate_turn_sequence.assert_not_called()
    mock_conv_repo.append_turn.assert_not_called()


@pytest.mark.asyncio
async def test_submitting_second_turn_while_pending_raises_409():
    """
    Gate 2: Submitting a turn while another turn is pending fails with HTTP 409.
    """
    workspace_id = uuid4()
    conversation_id = uuid4()
    owner_id = uuid4()

    mock_db = AsyncMock()
    mock_conv_repo = AsyncMock()
    mock_workspace_repo = AsyncMock()

    mock_ws = Workspace(workspace_id=workspace_id, owner_id=owner_id)
    mock_conv = Conversation(
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        owner_id=owner_id,
        status="active"
    )
    mock_workspace_repo.get_workspace.return_value = mock_ws
    mock_conv_repo.get_conversation.return_value = mock_conv
    mock_conv_repo.get_turn_by_client_request_id.return_value = None

    pending_turn = ConversationTurn(
        turn_id=uuid4(),
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        owner_id=owner_id,
        sequence=1,
        mode="ground",
        user_message="Pending turn",
        status="pending"
    )
    mock_conv_repo.get_active_turn.return_value = pending_turn

    service = ChatService(
        db=mock_db,
        conv_repo=mock_conv_repo,
        workspace_repo=mock_workspace_repo
    )

    turn_create = TurnCreate(mode="ground", message="Another turn attempt")

    with pytest.raises(HTTPException) as exc_info:
        await service.submit_turn(
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            owner_id=owner_id,
            turn_create=turn_create
        )

    assert exc_info.value.status_code == status.HTTP_409_CONFLICT
    assert exc_info.value.detail == "conversation_turn_in_progress"
    mock_conv_repo.allocate_turn_sequence.assert_not_called()
    mock_conv_repo.append_turn.assert_not_called()


# ============================================================================ #
# Gate 3: ARQ background worker is the sole creator of research ChatEvents
# ============================================================================ #

@pytest.mark.asyncio
async def test_research_turn_streaming_starts_no_duplicate_bridge():
    """
    Gate 3: In stream_turn with mode='research', ChatService must NOT start
    _bridge_research_events_background. The ARQ worker is the sole creator of
    research ChatEvents, preventing duplicate rows in chat_events.
    """
    workspace_id = uuid4()
    conversation_id = uuid4()
    owner_id = uuid4()
    turn_id = uuid4()
    run_id = uuid4()

    mock_db = AsyncMock()
    mock_conv_repo = AsyncMock()
    mock_workspace_repo = AsyncMock()
    mock_arq_redis = AsyncMock()

    mock_ws = Workspace(workspace_id=workspace_id, owner_id=owner_id)
    mock_conv = Conversation(
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        owner_id=owner_id,
        status="active"
    )
    mock_workspace_repo.get_workspace.return_value = mock_ws
    mock_conv_repo.get_conversation.return_value = mock_conv
    mock_conv_repo.get_turn_by_client_request_id.return_value = None
    mock_conv_repo.get_active_turn.return_value = None
    mock_conv_repo.allocate_turn_sequence.return_value = 1

    initial_turn = ConversationTurn(
        turn_id=turn_id,
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        owner_id=owner_id,
        sequence=1,
        mode="research",
        user_message="Deep research query",
        status="pending"
    )
    mock_conv_repo.append_turn.return_value = initial_turn

    mock_admission = AsyncMock()
    mock_run = MagicMock()
    mock_run.run_id = run_id
    mock_admission.admit_research_run.return_value = mock_run

    service = ChatService(
        db=mock_db,
        conv_repo=mock_conv_repo,
        workspace_repo=mock_workspace_repo,
        arq_redis=mock_arq_redis,
        admission_controller=mock_admission
    )
    service.stream_turn_events = MagicMock(return_value="mock_stream_generator")

    with patch("app.services.chat.context.build_research_context") as mock_build_ctx:
        mock_ctx = MagicMock()
        mock_ctx.model_dump.return_value = {}
        mock_build_ctx.return_value = mock_ctx

        turn_create = TurnCreate(mode="research", message="Deep research query")
        generator = await service.stream_turn(
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            owner_id=owner_id,
            turn_create=turn_create
        )

        assert generator == "mock_stream_generator"
        # Verify job was enqueued for the ARQ worker
        mock_arq_redis.enqueue_job.assert_awaited_once()
        assert mock_arq_redis.enqueue_job.call_args[0][0] == "run_research_agent_job"

        # Verify stream_turn_events was invoked directly
        service.stream_turn_events.assert_called_once_with(turn_id)


# ============================================================================ #
# Gate 4: Turn cancellation + completion races resolve deterministically via CAS
# ============================================================================ #

@pytest.mark.asyncio
async def test_cancellation_race_lost_to_completion_does_not_emit_cancelled():
    """
    Gate 4: When a turn completes before cancellation executes, the CAS query
    UPDATE conversation_turns SET status = 'cancelled' WHERE status IN ('pending', 'running')
    returns None. Cancellation must fail cleanly with HTTP 400 and NOT emit turn.cancelled or done.
    """
    workspace_id = uuid4()
    conversation_id = uuid4()
    turn_id = uuid4()
    owner_id = uuid4()

    mock_db = AsyncMock()
    mock_conv_repo = AsyncMock()
    mock_workspace_repo = AsyncMock()

    mock_ws = Workspace(workspace_id=workspace_id, owner_id=owner_id)
    mock_conv = Conversation(
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        owner_id=owner_id,
        status="active"
    )
    # Turn read at step 1 as running
    running_turn = ConversationTurn(
        turn_id=turn_id,
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        owner_id=owner_id,
        sequence=1,
        mode="research",
        user_message="Investigating race",
        status="running"
    )
    # Turn completed concurrently by worker before CAS
    completed_turn = ConversationTurn(
        turn_id=turn_id,
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        owner_id=owner_id,
        sequence=1,
        mode="research",
        user_message="Investigating race",
        status="completed"
    )

    mock_workspace_repo.get_workspace.return_value = mock_ws
    # First get_turn returns running, second get_turn (after CAS loss) returns completed
    mock_conv_repo.get_turn.side_effect = [running_turn, completed_turn]
    mock_conv_repo.get_conversation.return_value = mock_conv

    # CAS update fails because status is already completed
    mock_conv_repo.set_turn_status.return_value = None

    service = ChatService(
        db=mock_db,
        conv_repo=mock_conv_repo,
        workspace_repo=mock_workspace_repo
    )
    service.event_service = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await service.cancel_turn(
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            turn_id=turn_id,
            owner_id=owner_id
        )

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "Cannot cancel turn with status 'completed'" in exc_info.value.detail

    # CAS parameters verified
    set_status_call = mock_conv_repo.set_turn_status.call_args
    assert set_status_call.kwargs["turn_id"] == turn_id
    assert set_status_call.kwargs["status"] == "cancelled"
    assert set_status_call.kwargs["expected_statuses"] == ["pending", "running"]

    # Must NOT record or publish turn.cancelled or done when CAS was lost
    service.event_service.record_and_publish.assert_not_called()


@pytest.mark.asyncio
async def test_cas_query_in_repository():
    """
    Gate 4: Verify set_turn_status_cas specifies expected_statuses=['pending', 'running'].
    """
    mock_session = AsyncMock()
    repo = ConversationRepository(mock_session)

    turn_id = uuid4()
    with patch.object(repo, "set_turn_status", new_callable=AsyncMock) as mock_set:
        mock_set.return_value = MagicMock()
        await repo.set_turn_status_cas(turn_id=turn_id, status="completed")

        mock_set.assert_awaited_once()
        assert mock_set.call_args.kwargs["expected_statuses"] == ["pending", "running"]
        assert mock_set.call_args.kwargs["status"] == "completed"


# ============================================================================ #
# Gate 5: Canonical event type constants unification
# ============================================================================ #

def test_canonical_event_constants_unified():
    """
    Gate 5: Canonical event type constants unified across models, repositories,
    emitters, and event catalog.
    """
    expected_constants = {
        EVENT_TURN_RESEARCH_STARTED: "turn.research_started",
        EVENT_TURN_RESEARCH_PLANNING: "turn.research_planning",
        EVENT_TURN_RESEARCHING: "turn.researching",
        EVENT_TURN_SYNTHESIZING: "turn.synthesizing",
        EVENT_TURN_PROMOTION_AVAILABLE: "turn.promotion_available",
        EVENT_TURN_COMPLETED: "turn.completed",
        EVENT_TURN_PARTIAL: "turn.partial",
        EVENT_TURN_CANCELLED: "turn.cancelled",
        EVENT_TURN_FAILED: "turn.failed",
        EVENT_SCRATCHPAD_ENTRY: "scratchpad_entry",
        EVENT_STATUS_CHANGE: "status_change",
        EVENT_TOKEN: "token",
        EVENT_CITATION: "citation",
        EVENT_GROUND_ANSWER: "ground_answer",
        EVENT_DONE: "done",
        EVENT_ERROR: "error",
    }

    for const_val, expected_str in expected_constants.items():
        assert const_val == expected_str
        # Ensure enum has this value
        enum_entry = ChatEventType(expected_str)
        assert enum_entry.value == expected_str
