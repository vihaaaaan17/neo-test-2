import pytest
import pytest_asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.main import app
from app.core.database import async_session_maker
from app.models.workspace import Workspace
from app.models.conversation import Conversation, ConversationTurn
from app.models.open_notebook_binding import OpenNotebookWorkspaceBinding, OpenNotebookConversationBinding
from app.models.research import ResearchRun
from app.api.deps.auth import get_current_user
from app.api.deps.arq import get_arq_redis

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


@pytest_asyncio.fixture
async def db_session():
    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def test_env(db_session: AsyncSession):
    # Ensure active runs quota headroom by completing stale test runs
    await db_session.execute(
        update(ResearchRun)
        .where(ResearchRun.status.in_(["pending", "planning", "researching", "synthesizing", "finalizing"]))
        .values(status="completed")
    )

    user_a = uuid.uuid4()
    user_b = uuid.uuid4()

    ws_a = Workspace(workspace_id=uuid.uuid4(), owner_id=user_a, research_engine="legacy")
    ws_b = Workspace(workspace_id=uuid.uuid4(), owner_id=user_b, research_engine="legacy")
    db_session.add(ws_a)
    db_session.add(ws_b)
    await db_session.commit()
    await db_session.refresh(ws_a)
    await db_session.refresh(ws_b)

    # Active Open Notebook workspace binding for ws_a
    ws_binding = OpenNotebookWorkspaceBinding(
        workspace_id=ws_a.workspace_id,
        open_notebook_notebook_id=f"notebook:{uuid.uuid4()}",
        status="ACTIVE"
    )
    db_session.add(ws_binding)

    # Active conversation in ws_a
    conv_a = Conversation(
        conversation_id=uuid.uuid4(),
        workspace_id=ws_a.workspace_id,
        owner_id=user_a,
        title="Active Conv A",
        status="active"
    )
    db_session.add(conv_a)

    await db_session.commit()
    await db_session.refresh(conv_a)

    return {
        "user_a": user_a,
        "user_b": user_b,
        "ws_a": ws_a,
        "ws_b": ws_b,
        "conv_a": conv_a,
    }


class MockArqRedis:
    def __init__(self):
        self.jobs = []

    async def enqueue_job(self, function, *args, **kwargs):
        self.jobs.append((function, args, kwargs))


@pytest.fixture(autouse=True)
def mock_arq_redis_fixture():
    mock_redis = MockArqRedis()
    app.dependency_overrides[get_arq_redis] = lambda: mock_redis
    yield mock_redis
    app.dependency_overrides.pop(get_arq_redis, None)


# ============================================================================ #
# 1. Ground Turn Execution & Open Notebook 409 Transparent Recovery
# ============================================================================ #

async def test_ground_turn_execution(test_env, db_session: AsyncSession):
    user_a = test_env["user_a"]
    ws_a = test_env["ws_a"]
    conv_a = test_env["conv_a"]

    app.dependency_overrides[get_current_user] = lambda: user_a

    evidence_id = str(uuid.uuid4())
    mock_chat_res = {
        "answer": "This is a grounded answer from Open Notebook.",
        "evidence": [{"source_id": evidence_id, "title": "Spec Sheet"}]
    }

    try:
        with patch("app.services.chat.service.OpenNotebookClient.create_chat_session", new_callable=AsyncMock) as mock_create_sess, \
             patch("app.services.chat.service.OpenNotebookClient.chat_execute", new_callable=AsyncMock) as mock_exec:
            sess_id = f"session:{uuid.uuid4()}"
            mock_create_sess.return_value = sess_id
            mock_exec.return_value = mock_chat_res

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(
                    f"/api/v1/workspaces/{ws_a.workspace_id}/conversations/{conv_a.conversation_id}/turns",
                    json={"message": "What is the project architecture?", "mode": "ground"}
                )

                assert resp.status_code == 200, resp.text
                data = resp.json()
                assert data["status"] == "completed"
                assert data["mode"] == "ground"
                assert data["sequence"] == 1
                assert data["assistant_message"] == "This is a grounded answer from Open Notebook."
                assert len(data["ground_evidence_refs"]) == 1
                assert data["ground_evidence_refs"][0]["source_id"] == evidence_id

                # Verify DB binding was created
                binding = await db_session.get(OpenNotebookConversationBinding, conv_a.conversation_id)
                assert binding is not None
                assert binding.open_notebook_session_id == sess_id
    finally:
        app.dependency_overrides.pop(get_current_user, None)


async def test_ground_turn_409_rehydration_transparent_recovery(test_env, db_session: AsyncSession):
    user_a = test_env["user_a"]
    ws_a = test_env["ws_a"]
    conv_a = test_env["conv_a"]

    # Pre-existing session binding that has expired upstream
    stale_sess_id = f"session:stale_{uuid.uuid4()}"
    rehydrated_sess_id = f"session:rehydrated_{uuid.uuid4()}"
    initial_binding = OpenNotebookConversationBinding(
        conversation_id=conv_a.conversation_id,
        open_notebook_session_id=stale_sess_id
    )
    db_session.add(initial_binding)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: user_a

    try:
        with patch("app.services.chat.service.OpenNotebookClient.create_chat_session", new_callable=AsyncMock) as mock_create_sess, \
             patch("app.services.chat.service.OpenNotebookClient.chat_execute", new_callable=AsyncMock) as mock_exec:

            # First call raises 409 session_state_lost; second call succeeds after rehydration
            mock_exec.side_effect = [
                HTTPException(status_code=409, detail="session_state_lost"),
                {"answer": "Recovered answer after session rehydration", "evidence": []}
            ]
            mock_create_sess.return_value = rehydrated_sess_id

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(
                    f"/api/v1/workspaces/{ws_a.workspace_id}/conversations/{conv_a.conversation_id}/turns",
                    json={"message": "Can you hear me now?", "mode": "ground"}
                )

                assert resp.status_code == 200, resp.text
                data = resp.json()
                assert data["status"] == "completed"
                assert data["assistant_message"] == "Recovered answer after session rehydration"

                # Verify binding was updated to the new session
                await db_session.refresh(initial_binding)
                assert initial_binding.open_notebook_session_id == rehydrated_sess_id
                assert mock_exec.call_count == 2
                mock_create_sess.assert_called_once()
    finally:
        app.dependency_overrides.pop(get_current_user, None)


# ============================================================================ #
# 2. Research Turn Execution, Run Linkage, and ARQ Enqueueing
# ============================================================================ #

async def test_research_turn_execution(test_env, db_session: AsyncSession):
    user_a = test_env["user_a"]
    ws_a = test_env["ws_a"]
    conv_a = test_env["conv_a"]

    mock_redis = MockArqRedis()
    app.dependency_overrides[get_current_user] = lambda: user_a
    app.dependency_overrides[get_arq_redis] = lambda: mock_redis

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                f"/api/v1/workspaces/{ws_a.workspace_id}/conversations/{conv_a.conversation_id}/turns",
                json={
                    "message": "Investigate consensus algorithms in distributed storage",
                    "mode": "research"
                }
            )

            assert resp.status_code == 202, resp.text
            data = resp.json()
            assert data["status"] == "running"
            assert data["mode"] == "research"
            assert data["research_run_id"] is not None

            # Verify ResearchRun was created and linked to turn and conversation
            run_id = uuid.UUID(data["research_run_id"])
            run = await db_session.get(ResearchRun, run_id)
            assert run is not None
            assert run.workspace_id == ws_a.workspace_id
            assert run.owner_id == user_a
            assert run.conversation_id == conv_a.conversation_id
            assert run.turn_id == uuid.UUID(data["turn_id"])

            # Verify ARQ job enqueueing to research-standard queue
            assert len(mock_redis.jobs) == 1
            job_func, job_args, job_kwargs = mock_redis.jobs[0]
            assert job_func == "run_research_agent_job"
            assert job_kwargs["_queue_name"] == "research-standard"
            assert job_kwargs["run_id"] == str(run_id)
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_arq_redis, None)


# ============================================================================ #
# 3. Monotonic Sequence Allocation & Idempotency
# ============================================================================ #

async def test_monotonic_sequence_allocation(test_env, db_session: AsyncSession):
    user_a = test_env["user_a"]
    ws_a = test_env["ws_a"]
    conv_a = test_env["conv_a"]

    mock_redis = MockArqRedis()
    app.dependency_overrides[get_current_user] = lambda: user_a
    app.dependency_overrides[get_arq_redis] = lambda: mock_redis

    try:
        with patch("app.services.chat.service.OpenNotebookClient.create_chat_session", new_callable=AsyncMock) as mock_create_sess, \
             patch("app.services.chat.service.OpenNotebookClient.chat_execute", new_callable=AsyncMock) as mock_exec:
            mock_create_sess.return_value = f"session:seq_{uuid.uuid4()}"
            mock_exec.return_value = {"answer": "Ground response", "evidence": []}

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                # Turn 1: Ground
                r1 = await client.post(
                    f"/api/v1/workspaces/{ws_a.workspace_id}/conversations/{conv_a.conversation_id}/turns",
                    json={"message": "First prompt", "mode": "ground"}
                )
                assert r1.status_code == 200
                assert r1.json()["sequence"] == 1

                # Turn 2: Research
                r2 = await client.post(
                    f"/api/v1/workspaces/{ws_a.workspace_id}/conversations/{conv_a.conversation_id}/turns",
                    json={"message": "Second prompt", "mode": "research"}
                )
                assert r2.status_code == 202
                assert r2.json()["sequence"] == 2

                # Turn 3: Ground
                r3 = await client.post(
                    f"/api/v1/workspaces/{ws_a.workspace_id}/conversations/{conv_a.conversation_id}/turns",
                    json={"message": "Third prompt", "mode": "ground"}
                )
                assert r3.status_code == 200
                assert r3.json()["sequence"] == 3

                # Verify Conversation last_turn_sequence is 3
                await db_session.refresh(conv_a)
                assert conv_a.last_turn_sequence == 3
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_arq_redis, None)


async def test_idempotency_via_client_request_id(test_env):
    user_a = test_env["user_a"]
    ws_a = test_env["ws_a"]
    conv_a = test_env["conv_a"]

    app.dependency_overrides[get_current_user] = lambda: user_a
    client_req_id = f"idem-key-{uuid.uuid4()}"

    try:
        with patch("app.services.chat.service.OpenNotebookClient.create_chat_session", new_callable=AsyncMock) as mock_create_sess, \
             patch("app.services.chat.service.OpenNotebookClient.chat_execute", new_callable=AsyncMock) as mock_exec:
            mock_create_sess.return_value = f"session:idem_{uuid.uuid4()}"
            mock_exec.return_value = {"answer": "Idempotent answer", "evidence": []}

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                # First submission
                resp1 = await client.post(
                    f"/api/v1/workspaces/{ws_a.workspace_id}/conversations/{conv_a.conversation_id}/turns",
                    json={
                        "message": "Do this once",
                        "mode": "ground",
                        "client_request_id": client_req_id
                    }
                )
                assert resp1.status_code == 200
                turn1_id = resp1.json()["turn_id"]
                turn1_seq = resp1.json()["sequence"]

                # Second submission with the same client_request_id
                resp2 = await client.post(
                    f"/api/v1/workspaces/{ws_a.workspace_id}/conversations/{conv_a.conversation_id}/turns",
                    json={
                        "message": "Do this once duplicate",
                        "mode": "ground",
                        "client_request_id": client_req_id
                    }
                )
                assert resp2.status_code == 200
                assert resp2.json()["turn_id"] == turn1_id
                assert resp2.json()["sequence"] == turn1_seq
                # chat_execute should only have been called once
                assert mock_exec.call_count == 1
    finally:
        app.dependency_overrides.pop(get_current_user, None)


# ============================================================================ #
# 4. Turn Listing and Retrieval
# ============================================================================ #

async def test_list_and_get_turns(test_env):
    user_a = test_env["user_a"]
    ws_a = test_env["ws_a"]
    conv_a = test_env["conv_a"]

    app.dependency_overrides[get_current_user] = lambda: user_a

    try:
        with patch("app.services.chat.service.OpenNotebookClient.create_chat_session", new_callable=AsyncMock) as mock_create_sess, \
             patch("app.services.chat.service.OpenNotebookClient.chat_execute", new_callable=AsyncMock) as mock_exec:
            mock_create_sess.return_value = f"session:list_{uuid.uuid4()}"
            mock_exec.return_value = {"answer": "Some answer", "evidence": []}

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                # Create 2 turns
                r1 = await client.post(
                    f"/api/v1/workspaces/{ws_a.workspace_id}/conversations/{conv_a.conversation_id}/turns",
                    json={"message": "Turn 1", "mode": "ground"}
                )
                turn1_id = r1.json()["turn_id"]

                r2 = await client.post(
                    f"/api/v1/workspaces/{ws_a.workspace_id}/conversations/{conv_a.conversation_id}/turns",
                    json={"message": "Turn 2", "mode": "ground"}
                )
                turn2_id = r2.json()["turn_id"]

                # List turns
                list_resp = await client.get(
                    f"/api/v1/workspaces/{ws_a.workspace_id}/conversations/{conv_a.conversation_id}/turns"
                )
                assert list_resp.status_code == 200
                data = list_resp.json()
                assert data["total"] == 2
                assert len(data["turns"]) == 2
                assert data["turns"][0]["turn_id"] == turn1_id
                assert data["turns"][1]["turn_id"] == turn2_id

                # Get turn by ID
                get_resp = await client.get(
                    f"/api/v1/workspaces/{ws_a.workspace_id}/conversations/{conv_a.conversation_id}/turns/{turn1_id}"
                )
                assert get_resp.status_code == 200
                assert get_resp.json()["turn_id"] == turn1_id
    finally:
        app.dependency_overrides.pop(get_current_user, None)


# ============================================================================ #
# 5. Tenant Isolation & Archived Conversation Protection
# ============================================================================ #

async def test_archived_conversation_rejects_turns(test_env, db_session: AsyncSession):
    user_a = test_env["user_a"]
    ws_a = test_env["ws_a"]
    conv_a = test_env["conv_a"]

    conv_a.status = "archived"
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: user_a
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                f"/api/v1/workspaces/{ws_a.workspace_id}/conversations/{conv_a.conversation_id}/turns",
                json={"message": "Hello to archived conv", "mode": "ground"}
            )
            assert resp.status_code == 400
            assert "Cannot submit turn to archived conversation" in resp.text
    finally:
        app.dependency_overrides.pop(get_current_user, None)


async def test_cross_tenant_turn_access_rejected(test_env):
    user_b = test_env["user_b"]
    ws_a = test_env["ws_a"]
    conv_a = test_env["conv_a"]

    # User B tries to submit turn to User A's conversation
    app.dependency_overrides[get_current_user] = lambda: user_b
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                f"/api/v1/workspaces/{ws_a.workspace_id}/conversations/{conv_a.conversation_id}/turns",
                json={"message": "Hacker prompt", "mode": "ground"}
            )
            assert resp.status_code in [403, 404]

            # User B tries to list turns in User A's conversation
            list_resp = await client.get(
                f"/api/v1/workspaces/{ws_a.workspace_id}/conversations/{conv_a.conversation_id}/turns"
            )
            assert list_resp.status_code in [403, 404]
    finally:
        app.dependency_overrides.pop(get_current_user, None)
