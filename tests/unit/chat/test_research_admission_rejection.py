"""A research turn rejected by admission must not stay pending (it would block the conversation with 409)."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.conversation import Conversation, ConversationTurn
from app.models.workspace import Workspace
from app.schemas.chat import TurnCreate
from app.services.chat.service import ChatService


@pytest.mark.asyncio
async def test_admission_rejection_closes_the_turn_and_reraises():
    workspace_id, conversation_id, user_id, turn_id = uuid4(), uuid4(), uuid4(), uuid4()

    conv_repo = AsyncMock()
    conv_repo.get_conversation = AsyncMock(return_value=Conversation(
        conversation_id=conversation_id, workspace_id=workspace_id, owner_id=user_id,
        last_turn_sequence=0, status="active",
    ))
    conv_repo.get_turn_by_client_request_id = AsyncMock(return_value=None)
    conv_repo.allocate_turn_sequence = AsyncMock(return_value=1)
    conv_repo.append_turn = AsyncMock(return_value=ConversationTurn(
        turn_id=turn_id, conversation_id=conversation_id, workspace_id=workspace_id,
        owner_id=user_id, sequence=1, mode="research", user_message="hi", status="pending",
    ))
    conv_repo.set_turn_status = AsyncMock()

    workspace_repo = AsyncMock()
    workspace_repo.get_workspace = AsyncMock(return_value=Workspace(workspace_id=workspace_id, owner_id=user_id))

    admission = AsyncMock()
    admission.admit_research_run = AsyncMock(
        side_effect=HTTPException(status_code=422, detail="unsupported_research_engine")
    )

    with patch("app.services.chat.service.ChatEventRepository"), patch("app.services.chat.service.ChatEventService"):
        service = ChatService(
            db=AsyncMock(), conv_repo=conv_repo, workspace_repo=workspace_repo,
            research_repo=AsyncMock(), arq_redis=AsyncMock(), admission_controller=admission,
        )
        service.event_service = AsyncMock()

        with pytest.raises(HTTPException) as exc:
            await service.submit_turn(
                workspace_id=workspace_id, conversation_id=conversation_id, owner_id=user_id,
                turn_create=TurnCreate(mode="research", message="hi", research_options={"engine": "legacy"}),
                stream=False,
            )

    assert exc.value.status_code == 422
    kwargs = conv_repo.set_turn_status.await_args.kwargs
    assert kwargs["turn_id"] == turn_id
    assert kwargs["status"] == "failed"
    assert kwargs["expected_statuses"] == ["pending"]
    assert kwargs["error_code"] == "unsupported_research_engine"
