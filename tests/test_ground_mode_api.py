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
    from app.core.config import settings
    orig_on = settings.OPEN_NOTEBOOK_ENABLED
    settings.OPEN_NOTEBOOK_ENABLED = False

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
    
    settings.OPEN_NOTEBOOK_ENABLED = orig_on
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
    assert response.headers.get("Deprecation") == "true"
    assert "conversations" in response.headers.get("Link", "")
    data = response.json()
    assert data["answer"] == "This is a mock answer"
    assert data["evidence"] == [str(mock_gateways)]
    assert data.get("knowledge_id") is None
    
    # Chapter 4 Invariant: Ground turns do NOT enqueue sync_knowledge_to_graph_job
    enqueued_jobs = [call[0][0] for call in mock_arq_redis.enqueue_job.call_args_list]
    assert "sync_knowledge_to_graph_job" not in enqueued_jobs

    # Verify conversation turn was durably created in PostgreSQL
    async with async_session_maker() as session:
        from app.models.conversation import ConversationTurn
        from sqlalchemy import select
        turn_stmt = select(ConversationTurn).where(ConversationTurn.workspace_id == workspace_id)
        turn = (await session.execute(turn_stmt)).scalars().first()
        assert turn is not None
        assert turn.status in ("completed", "done")
        assert turn.assistant_message == "This is a mock answer"
        assert turn.ground_evidence_refs == [mock_gateways] or turn.ground_evidence_refs == [str(mock_gateways)]
