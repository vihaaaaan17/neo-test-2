import sys
from unittest.mock import MagicMock
sys.modules['pgvector'] = MagicMock()
sys.modules['pgvector.sqlalchemy'] = MagicMock()
sys.modules['aioboto3'] = MagicMock()
sys.modules['docling'] = MagicMock()
sys.modules['docling.document_converter'] = MagicMock()
sys.modules['litellm'] = MagicMock()
sys.modules['neo4j'] = MagicMock()
sys.modules['langgraph'] = MagicMock()
sys.modules['langgraph.graph'] = MagicMock()

import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone

from app.main import app
from app.core.config import settings
from app.api.routes.workspaces import get_workspace_repository
from app.api.deps.auth import get_current_user

pytestmark = pytest.mark.asyncio

TEST_USER_ID = uuid.uuid4()

def mock_get_current_user():
    return TEST_USER_ID

class MockWorkspace:
    def __init__(self, owner_id):
        self.workspace_id = uuid.uuid4()
        self.owner_id = owner_id
        self.status = "active"
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

class MockWorkspaceRepository:
    def __init__(self):
        self.db = {}

    async def create_workspace(self, owner_id):
        ws = MockWorkspace(owner_id)
        self.db[ws.workspace_id] = ws
        return ws

    async def get_workspace(self, workspace_id, owner_id):
        ws = self.db.get(workspace_id)
        if ws and ws.owner_id == owner_id and ws.status != "archived":
            return ws
        return None

mock_repo = MockWorkspaceRepository()
app.dependency_overrides[get_workspace_repository] = lambda: mock_repo
app.dependency_overrides[get_current_user] = mock_get_current_user

@pytest.fixture
async def setup_workspace():
    ws = await mock_repo.create_workspace(TEST_USER_ID)
    
    # We must patch the DB dependency inside ground_engine to return a valid binding
    # since we are skipping the actual db_session execution
    return ws

async def test_tenant_isolation_open_notebook(setup_workspace):
    workspace = setup_workspace
    
    original_flag = settings.OPEN_NOTEBOOK_ENABLED
    settings.OPEN_NOTEBOOK_ENABLED = True

    try:
        # Override current user to simulate User B
        app.dependency_overrides[get_current_user] = lambda: uuid.uuid4()
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/workspaces/{workspace.workspace_id}/ask",
                json={"query": "Test"}
            )
            assert response.status_code == 404
    finally:
        settings.OPEN_NOTEBOOK_ENABLED = original_flag
        app.dependency_overrides[get_current_user] = mock_get_current_user

async def test_partial_provenance_handling(setup_workspace):
    workspace = setup_workspace
    
    original_flag = settings.OPEN_NOTEBOOK_ENABLED
    settings.OPEN_NOTEBOOK_ENABLED = True

    with patch("app.integrations.open_notebook.ground_engine.OpenNotebookClient") as mock_client_cls, \
         patch("app.integrations.open_notebook.ground_engine.map_citations", new_callable=AsyncMock) as mock_map, \
         patch("app.integrations.open_notebook.ground_engine.AsyncSession") as mock_db:
        
        mock_client = mock_client_cls.return_value
        mock_client.get_default_models = AsyncMock(return_value={"default_chat_model": "test"})
        mock_client.search = AsyncMock(return_value=[{"id": "mapped-1"}, {"id": "unmapped-2"}])
        mock_client.ask_simple = AsyncMock(return_value={"answer": "Partial answer"})

        mapped_uuid = uuid.uuid4()
        mock_map.return_value = ([mapped_uuid], True)

        mock_binding = MagicMock()
        mock_db.execute = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.execute.return_value.scalars = MagicMock()
        mock_db.execute.return_value.scalars.return_value.first.return_value = mock_binding
        mock_db.execute.return_value.scalar = MagicMock(return_value=0)

        # Mock memory router
        mock_memory_router = AsyncMock()
        mock_memory = MagicMock()
        mock_memory.knowledge_id = uuid.uuid4()
        mock_memory_router.route_to_memory.return_value = mock_memory

        from app.core.database import get_db
        from app.api.routes.workspaces import get_memory_router
        try:
            # Overriding the db and memory_router dependencies
            app.dependency_overrides[get_db] = lambda: mock_db
            app.dependency_overrides[get_memory_router] = lambda: mock_memory_router
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    f"/api/v1/workspaces/{workspace.workspace_id}/ask",
                    json={"query": "Test"}
                )
                assert response.status_code == 200
                data = response.json()
                assert data["answer"] == "Partial answer"
                assert str(mapped_uuid) in data["evidence"]
                assert data["provenance_status"] == "partial"
        finally:
            settings.OPEN_NOTEBOOK_ENABLED = original_flag
            app.dependency_overrides.pop(get_memory_router, None)

async def test_session_state_lost_409(setup_workspace):
    workspace = setup_workspace
    
    original_flag = settings.OPEN_NOTEBOOK_ENABLED
    settings.OPEN_NOTEBOOK_ENABLED = True

    with patch("app.integrations.open_notebook.ground_engine.OpenNotebookClient") as mock_client_cls, \
         patch("app.integrations.open_notebook.ground_engine.AsyncSession") as mock_db:
        
        from fastapi import HTTPException
        mock_client = mock_client_cls.return_value
        mock_client.get_default_models = AsyncMock(return_value={"default_chat_model": "test"})
        mock_client.search = AsyncMock(return_value=[])
        # The wrapper maps 404 to 409 session_state_lost
        mock_client.ask_simple = AsyncMock(side_effect=HTTPException(status_code=409, detail="session_state_lost"))

        mock_binding = MagicMock()
        mock_db.execute = AsyncMock()
        mock_db.execute.return_value.scalars = MagicMock()
        mock_db.execute.return_value.scalars.return_value.first.return_value = mock_binding

        from app.core.database import get_db
        try:
            app.dependency_overrides[get_db] = lambda: mock_db
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    f"/api/v1/workspaces/{workspace.workspace_id}/ask",
                    json={"query": "Test"}
                )
                assert response.status_code == 409
                assert response.json()["detail"] == "session_state_lost"
        finally:
            settings.OPEN_NOTEBOOK_ENABLED = original_flag
            app.dependency_overrides.pop(get_db, None)
