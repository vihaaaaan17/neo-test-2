import pytest
from httpx import AsyncClient, ASGITransport
from uuid import uuid4
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock

from app.main import app
from app.api.deps.auth import get_current_user
from app.api.deps.arq import get_arq_redis
from app.api.routes.workspaces import get_workspace_repository

@pytest.fixture
def mock_user_id():
    return uuid4()

@pytest.fixture
def mock_workspace_id():
    return uuid4()

@pytest.mark.asyncio
async def test_async_sse_research_flow(mock_user_id, mock_workspace_id):
    # Mock auth
    app.dependency_overrides[get_current_user] = lambda: mock_user_id
    
    # Mock Arq Redis & PubSub
    class MockPubSub:
        async def subscribe(self, channel):
            pass
        async def get_message(self, ignore_subscribe_messages=True, timeout=1.0):
            if not hasattr(self, "_events"):
                self._events = [
                    {"type": "message", "data": b'{"status": "starting", "message": "Initializing"}'},
                    {"type": "message", "data": b'{"status": "planning", "plan": ["q1"]}'},
                    {"type": "message", "data": b'{"status": "completed", "message": "done"}'}
                ]
            if self._events:
                return self._events.pop(0)
            # simulate waiting if out of events but connection is open (although we break on completed)
            await asyncio.sleep(0.1) 
            return None
        async def unsubscribe(self, channel):
            pass
        async def close(self):
            pass

    class MockArqRedis:
        async def enqueue_job(self, *args, **kwargs):
            return MagicMock()
        def pubsub(self):
            return MockPubSub()
            
    app.dependency_overrides[get_arq_redis] = lambda: MockArqRedis()
    
    mock_repo = MagicMock()
    mock_repo.get_workspace = AsyncMock(return_value=MagicMock())
    app.dependency_overrides[get_workspace_repository] = lambda: mock_repo
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Enqueue job
        resp = await ac.post(f"/api/v1/workspaces/{mock_workspace_id}/research", json={"objective": "Test"})
        assert resp.status_code == 202
        job_id = resp.json()["job_id"]
        
        # 2. Consume SSE Stream
        async with ac.stream("GET", f"/api/v1/jobs/{job_id}/stream") as stream_resp:
            assert stream_resp.status_code == 200
            chunks = []
            async for line in stream_resp.aiter_lines():
                if line.startswith("data: "):
                    data_str = line.removeprefix("data: ")
                    chunks.append(json.loads(data_str))
                    
            assert len(chunks) == 3
            assert chunks[0]["status"] == "starting"
            assert chunks[1]["status"] == "planning"
            assert chunks[2]["status"] == "completed"
