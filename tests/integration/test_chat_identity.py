import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings
from app.models.workspace import Workspace
from app.models.conversation import GroundConversation
from app.models.open_notebook_binding import OpenNotebookConversationBinding, OpenNotebookWorkspaceBinding
from sqlalchemy.ext.asyncio import AsyncSession
from tests.utils import create_test_user, get_user_token_headers
import uuid
from unittest.mock import patch, AsyncMock, MagicMock

pytestmark = pytest.mark.asyncio

@pytest.fixture
async def setup_workspace_with_on(db_session: AsyncSession):
    user = await create_test_user(db_session)
    token_headers = await get_user_token_headers(user, db_session)
    
    workspace = Workspace(
        workspace_id=uuid.uuid4(),
        owner_id=user.user_id,
        name="Chat Test Workspace"
    )
    db_session.add(workspace)
    
    ws_binding = OpenNotebookWorkspaceBinding(
        workspace_id=workspace.workspace_id,
        open_notebook_notebook_id="notebook:123",
        status="ACTIVE"
    )
    db_session.add(ws_binding)
    await db_session.commit()
    
    return workspace, token_headers, user

async def test_chat_new_conversation(setup_workspace_with_on, db_session: AsyncSession):
    workspace, token_headers, user = setup_workspace_with_on
    workspace_id = workspace.workspace_id
    
    with patch("app.integrations.open_notebook.client.OpenNotebookClient.create_chat_session", new_callable=AsyncMock) as mock_create:
        with patch("app.integrations.open_notebook.client.OpenNotebookClient.chat_execute", new_callable=AsyncMock) as mock_execute:
            mock_create.return_value = "session:456"
            mock_execute.return_value = {"answer": "Hello from ON", "messages": []}
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    f"/workspaces/{workspace_id}/chat",
                    headers=token_headers,
                    json={"message": "Hello"}
                )
                
                assert response.status_code == 200, response.text
                data = response.json()
                assert data["answer"] == "Hello from ON"
                assert "conversation_id" in data
                
                # Verify DB records
                conv_id = uuid.UUID(data["conversation_id"])
                conv = await db_session.get(GroundConversation, conv_id)
                assert conv is not None
                assert conv.workspace_id == workspace_id
                assert conv.owner_id == user.user_id
                
                binding = await db_session.get(OpenNotebookConversationBinding, conv_id)
                assert binding is not None
                assert binding.open_notebook_session_id == "session:456"

async def test_chat_existing_conversation(setup_workspace_with_on, db_session: AsyncSession):
    workspace, token_headers, user = setup_workspace_with_on
    workspace_id = workspace.workspace_id
    
    conv_id = uuid.uuid4()
    conv = GroundConversation(
        conversation_id=conv_id,
        workspace_id=workspace_id,
        owner_id=user.user_id
    )
    db_session.add(conv)
    
    binding = OpenNotebookConversationBinding(
        conversation_id=conv_id,
        open_notebook_session_id="session:789"
    )
    db_session.add(binding)
    await db_session.commit()
    
    with patch("app.integrations.open_notebook.client.OpenNotebookClient.chat_execute", new_callable=AsyncMock) as mock_execute:
        mock_execute.return_value = {"answer": "Follow-up answer", "messages": []}
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/workspaces/{workspace_id}/chat",
                headers=token_headers,
                json={"message": "Next part", "conversation_id": str(conv_id)}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["answer"] == "Follow-up answer"
            assert data["conversation_id"] == str(conv_id)
            
            mock_execute.assert_called_once_with(
                session_id="session:789",
                notebook_id="notebook:123",
                message="Next part"
            )

async def test_chat_session_expired(setup_workspace_with_on, db_session: AsyncSession):
    from fastapi import HTTPException
    workspace, token_headers, user = setup_workspace_with_on
    workspace_id = workspace.workspace_id
    
    conv_id = uuid.uuid4()
    conv = GroundConversation(
        conversation_id=conv_id,
        workspace_id=workspace_id,
        owner_id=user.user_id
    )
    db_session.add(conv)
    
    binding = OpenNotebookConversationBinding(
        conversation_id=conv_id,
        open_notebook_session_id="session:missing"
    )
    db_session.add(binding)
    await db_session.commit()
    
    with patch("app.integrations.open_notebook.client.OpenNotebookClient.chat_execute", new_callable=AsyncMock) as mock_execute:
        mock_execute.side_effect = HTTPException(status_code=400, detail="conversation_session_expired")
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/workspaces/{workspace_id}/chat",
                headers=token_headers,
                json={"message": "Are you there?", "conversation_id": str(conv_id)}
            )
            
            assert response.status_code == 400
            assert response.json()["detail"] == "conversation_session_expired"
