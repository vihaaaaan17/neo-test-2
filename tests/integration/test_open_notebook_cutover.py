import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings
from app.models.workspace import Workspace
from sqlalchemy.ext.asyncio import AsyncSession
from tests.utils import create_test_user, get_user_token_headers
import uuid

pytestmark = pytest.mark.asyncio

@pytest.fixture
async def setup_workspace(db_session: AsyncSession):
    user = await create_test_user(db_session)
    token_headers = await get_user_token_headers(user, db_session)
    
    workspace = Workspace(
        workspace_id=uuid.uuid4(),
        owner_id=user.user_id,
        name="Cutover Test Workspace"
    )
    db_session.add(workspace)
    await db_session.commit()
    
    return workspace, token_headers

async def test_ask_facade_fallback(setup_workspace):
    workspace, token_headers = setup_workspace
    original_flag = settings.OPEN_NOTEBOOK_ENABLED
    settings.OPEN_NOTEBOOK_ENABLED = False
    
    workspace_id = workspace.workspace_id
    
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/workspaces/{workspace_id}/ask",
                headers=token_headers,
                json={"query": "What is the capital of France?"}
            )
            assert response.status_code in [200, 422], "Should call the fallback orchestrator"
    finally:
        settings.OPEN_NOTEBOOK_ENABLED = original_flag


async def test_ask_facade_open_notebook_missing_binding(setup_workspace):
    workspace, token_headers = setup_workspace
    original_flag = settings.OPEN_NOTEBOOK_ENABLED
    settings.OPEN_NOTEBOOK_ENABLED = True
    
    workspace_id = workspace.workspace_id
    
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/workspaces/{workspace_id}/ask",
                headers=token_headers,
                json={"query": "What is the capital of France?"}
            )
            assert response.status_code == 400
            assert "Workspace does not have an active Open Notebook binding" in response.json()["detail"]
    finally:
        settings.OPEN_NOTEBOOK_ENABLED = original_flag


async def test_projection_status_route(setup_workspace):
    workspace, token_headers = setup_workspace
    workspace_id = workspace.workspace_id
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/workspaces/{workspace_id}/projection-status",
            headers=token_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert isinstance(data["status"], dict)

