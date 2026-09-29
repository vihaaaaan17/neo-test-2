import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from datetime import datetime, timezone
from fastapi import HTTPException

from app.api.routes.scratchpad import (
    create_scratchpad_entry,
    list_scratchpad_entries,
    get_scratchpad_entry,
    update_scratchpad_entry
)
from app.models.scratchpad import ScratchpadEntry
from app.models.workspace import Workspace
from app.models.conversation import Conversation
from app.schemas.scratchpad import ScratchpadEntryCreate, ScratchpadEntryUpdate


@pytest.mark.asyncio
async def test_create_scratchpad_entry_route():
    workspace_id = uuid4()
    conversation_id = uuid4()
    user_id = uuid4()
    entry_id = uuid4()

    mock_ws = Workspace(workspace_id=workspace_id, owner_id=user_id)
    mock_conv = Conversation(conversation_id=conversation_id, workspace_id=workspace_id, owner_id=user_id)
    mock_entry = ScratchpadEntry(
        entry_id=entry_id,
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        entry_type="hypothesis",
        lifecycle="active",
        content="Test hypothesis",
        is_pinned_to_workspace=False,
        metadata_={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    mock_session = AsyncMock()

    with patch("app.api.routes.scratchpad.WorkspaceRepository") as mock_ws_repo_cls, \
         patch("app.api.routes.scratchpad.ConversationRepository") as mock_conv_repo_cls, \
         patch("app.api.routes.scratchpad.ScratchpadRepository") as mock_sp_repo_cls:

        mock_ws_repo = mock_ws_repo_cls.return_value
        mock_ws_repo.get_workspace = AsyncMock(return_value=mock_ws)

        mock_conv_repo = mock_conv_repo_cls.return_value
        mock_conv_repo.get_conversation = AsyncMock(return_value=mock_conv)

        mock_sp_repo = mock_sp_repo_cls.return_value
        mock_sp_repo.create_entry = AsyncMock(return_value=mock_entry)

        payload = ScratchpadEntryCreate(
            entry_type="hypothesis",
            content="Test hypothesis"
        )
        res = await create_scratchpad_entry(
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            payload=payload,
            current_user=user_id,
            session=mock_session
        )

        assert res.entry_id == entry_id
        assert res.content == "Test hypothesis"
        mock_sp_repo.create_entry.assert_awaited_once()


@pytest.mark.asyncio
async def test_scratchpad_tenant_isolation_rejection():
    """
    If another user attempts to create a scratchpad entry in a workspace they don't own,
    it must return 404.
    """
    workspace_id = uuid4()
    conversation_id = uuid4()
    user_b = uuid4()

    mock_session = AsyncMock()

    with patch("app.api.routes.scratchpad.WorkspaceRepository") as mock_ws_repo_cls:
        mock_ws_repo = mock_ws_repo_cls.return_value
        mock_ws_repo.get_workspace = AsyncMock(return_value=None)  # Access denied / not found

        payload = ScratchpadEntryCreate(
            entry_type="note",
            content="Intruder note"
        )
        with pytest.raises(HTTPException) as exc_info:
            await create_scratchpad_entry(
                workspace_id=workspace_id,
                conversation_id=conversation_id,
                payload=payload,
                current_user=user_b,
                session=mock_session
            )
        assert exc_info.value.status_code == 404
