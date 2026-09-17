import pytest
from httpx import AsyncClient, ASGITransport
from uuid import uuid4
import json
from unittest.mock import AsyncMock

from app.main import app
from app.api.deps.llm import get_llm_gateway, get_embed_gateway
from app.api.routes.workspaces import get_hybrid_retrieval_service
from app.services.hybrid_retrieval import RetrievedChunk
from app.models.workspace import Workspace
from app.core.database import async_session_maker
from app.api.deps.auth import get_current_user
from app.api.deps.arq import get_arq_redis

@pytest.fixture
def mock_current_user():
    user_id = uuid4()
    app.dependency_overrides[get_current_user] = lambda: user_id
    yield user_id
    app.dependency_overrides.pop(get_current_user, None)

@pytest.fixture
def mock_arq_redis():
    mock = AsyncMock()
    app.dependency_overrides[get_arq_redis] = lambda: mock
    yield mock
    app.dependency_overrides.pop(get_arq_redis, None)

@pytest.fixture
def mock_gateways():
    evidence_id = uuid4()
    async def mock_llm(prompt: str):
        if "hallucination detection judge" in prompt:
            return "YES"
        return json.dumps({
            "answer": "This is a mock answer",
            "evidence": [str(evidence_id)]
        })
        
    async def mock_embed(text: str):
        return [0.1]
        
    class MockHybridRetrieval:
        async def retrieve(self, workspace_id, query_text, query_embedding):
            return [RetrievedChunk(block_id=evidence_id, text="Mock text", source_id=uuid4(), score=1.0)]
            
    app.dependency_overrides[get_llm_gateway] = lambda: mock_llm
    app.dependency_overrides[get_embed_gateway] = lambda: mock_embed
    app.dependency_overrides[get_hybrid_retrieval_service] = MockHybridRetrieval
    
    yield evidence_id
    
    app.dependency_overrides.pop(get_llm_gateway, None)
    app.dependency_overrides.pop(get_embed_gateway, None)
    app.dependency_overrides.pop(get_hybrid_retrieval_service, None)

@pytest.mark.asyncio
@pytest.mark.integration
async def test_ask_ground_mode_endpoint(mock_current_user, mock_arq_redis, mock_gateways):
    # Setup test workspace
    workspace_id = uuid4()
    async with async_session_maker() as session:
        ws = Workspace(workspace_id=workspace_id, owner_id=mock_current_user)
        session.add(ws)
        await session.commit()
        
    # Execute request
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"/api/v1/workspaces/{workspace_id}/ask", json={"query": "Test query"})
        
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "This is a mock answer"
    assert data["evidence"] == [str(mock_gateways)]
    assert "knowledge_id" in data
    
    # Verify graph sync worker was enqueued
    mock_arq_redis.enqueue_job.assert_called_once_with(
        "sync_knowledge_to_graph_job", 
        knowledge_id=data["knowledge_id"]
    )
