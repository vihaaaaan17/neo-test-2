import asyncio
import json
import pytest
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException, status

from app.models.conversation import Conversation, ConversationTurn
from app.models.workspace import Workspace
from app.models.research import ResearchRun
from app.services.chat.service import ChatService
from app.schemas.chat import TurnResponse
from app.api.routes.chat import cancel_turn as api_cancel_turn


@pytest.mark.asyncio
async def test_cancel_ground_turn_cancels_task_and_emits_events():
    """Cancelling a Ground turn cancels the running asyncio task and publishes turn.cancelled."""
    workspace_id = uuid4()
    conversation_id = uuid4()
    turn_id = uuid4()
    owner_id = uuid4()

    mock_db = AsyncMock()
    mock_conv_repo = AsyncMock()
    mock_workspace_repo = AsyncMock()
    mock_research_repo = AsyncMock()
    mock_arq_redis = AsyncMock()

    mock_workspace = Workspace(workspace_id=workspace_id, owner_id=owner_id)
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
        user_message="Test query",
        status="running",
        ground_evidence_refs=[],
        context_version={},
        created_at=datetime.now(timezone.utc)
    )

    mock_workspace_repo.get_workspace.return_value = mock_workspace
    mock_conv_repo.get_conversation.return_value = mock_conv
    mock_conv_repo.get_turn.return_value = mock_turn

    cancelled_turn_obj = ConversationTurn(
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
    mock_conv_repo.set_turn_status.return_value = cancelled_turn_obj

    # Create dummy running task
    async def dummy_coro():
        try:
            await asyncio.sleep(100)
        except asyncio.CancelledError:
            raise

    task = asyncio.create_task(dummy_coro())
    ChatService._running_tasks[turn_id] = task

    service = ChatService(
        db=mock_db,
        conv_repo=mock_conv_repo,
        workspace_repo=mock_workspace_repo,
        research_repo=mock_research_repo,
        arq_redis=mock_arq_redis
    )
    service.event_service = AsyncMock()

    result = await service.cancel_turn(workspace_id, conversation_id, turn_id, owner_id)
    # Yield to let the cancelled task process its cancellation
    await asyncio.sleep(0)

    assert task.cancelled()
    assert result.status == "cancelled"
    assert turn_id not in ChatService._running_tasks
    mock_conv_repo.set_turn_status.assert_awaited_once()
    assert mock_conv_repo.set_turn_status.call_args[1]["status"] == "cancelled"

    # Verify event service called for turn.cancelled and done
    event_calls = service.event_service.record_and_publish.await_args_list
    assert len(event_calls) == 2
    types = [c.kwargs.get("event_type") or (c.args[1] if len(c.args) > 1 else None) for c in event_calls]
    assert "turn.cancelled" in types
    assert "done" in types


@pytest.mark.asyncio
async def test_cancel_research_turn_transitions_run_and_emits_events():
    """Cancelling a Research turn cascades to ResearchRun, publishes cancellation to Redis, and emits turn.cancelled."""
    workspace_id = uuid4()
    conversation_id = uuid4()
    turn_id = uuid4()
    run_id = uuid4()
    owner_id = uuid4()

    mock_db = AsyncMock()
    mock_conv_repo = AsyncMock()
    mock_workspace_repo = AsyncMock()
    mock_research_repo = AsyncMock()
    mock_arq_redis = AsyncMock()

    mock_workspace = Workspace(workspace_id=workspace_id, owner_id=owner_id)
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
        user_message="Deep research query",
        status="running",
        research_run_id=run_id,
        ground_evidence_refs=[],
        context_version={},
        created_at=datetime.now(timezone.utc)
    )
    mock_run = ResearchRun(
        run_id=run_id,
        workspace_id=workspace_id,
        owner_id=owner_id,
        objective="Deep research query",
        status="running",
        engine="open_deep_research"
    )

    mock_workspace_repo.get_workspace.return_value = mock_workspace
    mock_conv_repo.get_conversation.return_value = mock_conv
    mock_conv_repo.get_turn.return_value = mock_turn
    mock_research_repo.get_run.return_value = mock_run

    cancelled_turn_obj = ConversationTurn(
        turn_id=turn_id,
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        owner_id=owner_id,
        sequence=1,
        mode="research",
        user_message="Deep research query",
        status="cancelled",
        research_run_id=run_id,
        ground_evidence_refs=[],
        context_version={},
        created_at=datetime.now(timezone.utc)
    )
    mock_conv_repo.set_turn_status.return_value = cancelled_turn_obj

    service = ChatService(
        db=mock_db,
        conv_repo=mock_conv_repo,
        workspace_repo=mock_workspace_repo,
        research_repo=mock_research_repo,
        arq_redis=mock_arq_redis
    )
    service.event_service = AsyncMock()

    with patch("app.services.research.lifecycle.ResearchLifecycleService.transition_run", new_callable=AsyncMock) as mock_transition:
        result = await service.cancel_turn(workspace_id, conversation_id, turn_id, owner_id)

        mock_transition.assert_awaited_once_with(
            workspace_id=workspace_id,
            run_id=run_id,
            target_status="cancelled",
            metadata={"reason": "Cancelled by user via turn cancellation endpoint"}
        )

    assert result.status == "cancelled"
    # Verify Redis publish for cooperative cancellation in worker engine
    publish_calls = mock_arq_redis.publish.await_args_list
    assert len(publish_calls) >= 1
    channels = [call[0][0] for call in publish_calls]
    assert f"research_cancellation:{run_id}" in channels

    # Verify event service called for turn.cancelled and done
    event_calls = service.event_service.record_and_publish.await_args_list
    assert len(event_calls) == 2
    types = [c.kwargs.get("event_type") or (c.args[1] if len(c.args) > 1 else None) for c in event_calls]
    assert "turn.cancelled" in types
    assert "done" in types


@pytest.mark.asyncio
async def test_cancel_turn_idempotent_if_already_cancelled():
    """Cancelling a turn that is already cancelled returns it cleanly without raising."""
    workspace_id = uuid4()
    conversation_id = uuid4()
    turn_id = uuid4()
    owner_id = uuid4()

    mock_db = AsyncMock()
    mock_conv_repo = AsyncMock()
    mock_workspace_repo = AsyncMock()

    mock_workspace = Workspace(workspace_id=workspace_id, owner_id=owner_id)
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

    mock_workspace_repo.get_workspace.return_value = mock_workspace
    mock_conv_repo.get_conversation.return_value = mock_conv
    mock_conv_repo.get_turn.return_value = already_cancelled_turn

    service = ChatService(
        db=mock_db,
        conv_repo=mock_conv_repo,
        workspace_repo=mock_workspace_repo
    )

    res = await service.cancel_turn(workspace_id, conversation_id, turn_id, owner_id)
    assert res.status == "cancelled"
    mock_conv_repo.set_turn_status.assert_not_called()


@pytest.mark.asyncio
async def test_cancel_turn_rejects_completed_or_failed():
    """Cancelling an already completed or failed turn raises HTTP 400 Bad Request."""
    workspace_id = uuid4()
    conversation_id = uuid4()
    turn_id = uuid4()
    owner_id = uuid4()

    mock_db = AsyncMock()
    mock_conv_repo = AsyncMock()
    mock_workspace_repo = AsyncMock()

    mock_workspace = Workspace(workspace_id=workspace_id, owner_id=owner_id)
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

    mock_workspace_repo.get_workspace.return_value = mock_workspace
    mock_conv_repo.get_conversation.return_value = mock_conv
    mock_conv_repo.get_turn.return_value = completed_turn

    service = ChatService(
        db=mock_db,
        conv_repo=mock_conv_repo,
        workspace_repo=mock_workspace_repo
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.cancel_turn(workspace_id, conversation_id, turn_id, owner_id)
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "Cannot cancel turn with status 'completed'" in exc_info.value.detail


@pytest.mark.asyncio
async def test_cancel_turn_validates_workspace_and_owner():
    """Tenant isolation is strictly enforced on turn cancellation."""
    workspace_id = uuid4()
    conversation_id = uuid4()
    turn_id = uuid4()
    owner_id = uuid4()
    wrong_owner_id = uuid4()

    mock_db = AsyncMock()
    mock_conv_repo = AsyncMock()
    mock_workspace_repo = AsyncMock()

    # Case 1: Workspace not found
    mock_workspace_repo.get_workspace.return_value = None
    service = ChatService(db=mock_db, conv_repo=mock_conv_repo, workspace_repo=mock_workspace_repo)
    with pytest.raises(HTTPException) as exc:
        await service.cancel_turn(workspace_id, conversation_id, turn_id, owner_id)
    assert exc.value.status_code == 404

    # Case 2: Conversation owned by someone else
    mock_workspace = Workspace(workspace_id=workspace_id, owner_id=owner_id)
    mock_conv = Conversation(
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        owner_id=wrong_owner_id,
        status="active"
    )
    mock_workspace_repo.get_workspace.return_value = mock_workspace
    mock_conv_repo.get_conversation.return_value = mock_conv
    with pytest.raises(HTTPException) as exc:
        await service.cancel_turn(workspace_id, conversation_id, turn_id, owner_id)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_api_cancel_turn_route_handler():
    """The API route handler POST /turns/{turn_id}/cancel delegates to chat_service.cancel_turn."""
    workspace_id = uuid4()
    conversation_id = uuid4()
    turn_id = uuid4()
    owner_id = uuid4()

    mock_service = AsyncMock()
    cancelled_turn = ConversationTurn(
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
    mock_service.cancel_turn.return_value = cancelled_turn

    response = await api_cancel_turn(
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        turn_id=turn_id,
        current_user_id=owner_id,
        chat_service=mock_service
    )

    assert isinstance(response, TurnResponse)
    assert response.turn_id == turn_id
    assert response.status == "cancelled"
    mock_service.cancel_turn.assert_awaited_once_with(
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        turn_id=turn_id,
        owner_id=owner_id
    )
