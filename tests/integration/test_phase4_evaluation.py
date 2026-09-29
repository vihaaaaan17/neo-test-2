import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.main import app
from app.core.config import settings
from app.models.workspace import Workspace
from app.models.open_notebook_binding import OpenNotebookWorkspaceBinding
from app.api.deps.auth import get_current_user
from tests.utils import create_test_user, get_user_token_headers

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def setup_workspace(db_session: AsyncSession):
    user = await create_test_user(db_session)
    token_headers = await get_user_token_headers(user, db_session)

    workspace = Workspace(
        workspace_id=uuid.uuid4(),
        owner_id=user.user_id,
        status="active"
    )
    db_session.add(workspace)
    await db_session.commit()

    return workspace, token_headers, user


async def test_tenant_isolation_open_notebook(setup_workspace, db_session: AsyncSession):
    workspace, _, _ = setup_workspace

    original_flag = settings.OPEN_NOTEBOOK_ENABLED
    settings.OPEN_NOTEBOOK_ENABLED = True

    user_b = await create_test_user(db_session)
    headers_b = await get_user_token_headers(user_b, db_session)

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/workspaces/{workspace.workspace_id}/ask",
                headers=headers_b,
                json={"query": "Test"}
            )
            assert response.status_code == 404
    finally:
        settings.OPEN_NOTEBOOK_ENABLED = original_flag


async def test_partial_provenance_handling(setup_workspace, db_session: AsyncSession):
    workspace, token_headers, user = setup_workspace

    # Create workspace binding
    binding = OpenNotebookWorkspaceBinding(
        workspace_id=workspace.workspace_id,
        open_notebook_notebook_id=f"nb_{uuid.uuid4().hex}"
    )
    db_session.add(binding)
    await db_session.commit()

    original_flag = settings.OPEN_NOTEBOOK_ENABLED
    settings.OPEN_NOTEBOOK_ENABLED = True

    with patch("app.integrations.open_notebook.ground_engine.OpenNotebookClient") as mock_client_cls, \
         patch("app.integrations.open_notebook.ground_engine.map_citations", new_callable=AsyncMock) as mock_map:

        mock_client = mock_client_cls.return_value
        mock_client.get_default_models = AsyncMock(return_value={"default_chat_model": "test"})
        mock_client.search = AsyncMock(return_value=[{"id": "mapped-1"}, {"id": "unmapped-2"}])
        mock_client.ask_simple = AsyncMock(return_value={"answer": "Partial answer"})

        mapped_uuid = uuid.uuid4()
        mock_map.return_value = ([mapped_uuid], True)

        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    f"/api/v1/workspaces/{workspace.workspace_id}/ask",
                    headers=token_headers,
                    json={"query": "Test"}
                )
                assert response.status_code == 200, response.text
                data = response.json()
                assert data["answer"] == "Partial answer"
                assert str(mapped_uuid) in data["evidence"]
                assert data["provenance_status"] == "partial"
        finally:
            settings.OPEN_NOTEBOOK_ENABLED = original_flag


async def test_session_state_lost_409(setup_workspace, db_session: AsyncSession):
    workspace, token_headers, _ = setup_workspace

    # Create workspace binding
    binding = OpenNotebookWorkspaceBinding(
        workspace_id=workspace.workspace_id,
        open_notebook_notebook_id=f"nb_{uuid.uuid4().hex}"
    )
    db_session.add(binding)
    await db_session.commit()

    original_flag = settings.OPEN_NOTEBOOK_ENABLED
    settings.OPEN_NOTEBOOK_ENABLED = True

    with patch("app.integrations.open_notebook.ground_engine.OpenNotebookClient") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.get_default_models = AsyncMock(return_value={"default_chat_model": "test"})
        mock_client.search = AsyncMock(return_value=[])
        # The wrapper maps 404 to 409 session_state_lost
        mock_client.ask_simple = AsyncMock(side_effect=HTTPException(status_code=409, detail="session_state_lost"))

        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    f"/api/v1/workspaces/{workspace.workspace_id}/ask",
                    headers=token_headers,
                    json={"query": "Test"}
                )
                assert response.status_code == 409
                assert response.json()["detail"] == "session_state_lost"
        finally:
            settings.OPEN_NOTEBOOK_ENABLED = original_flag
