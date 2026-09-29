import pytest
import pytest_asyncio
import uuid
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.core.database import async_session_maker
from app.models.workspace import Workspace
from app.repositories.conversation import ConversationRepository
from app.api.deps.auth import get_current_user

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


@pytest_asyncio.fixture
async def db_session():
    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def tenant_workspaces(db_session: AsyncSession):
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()

    ws_a = Workspace(workspace_id=uuid.uuid4(), owner_id=user_a)
    ws_b = Workspace(workspace_id=uuid.uuid4(), owner_id=user_b)

    db_session.add(ws_a)
    db_session.add(ws_b)
    await db_session.commit()
    await db_session.refresh(ws_a)
    await db_session.refresh(ws_b)

    return {
        "user_a": user_a,
        "user_b": user_b,
        "ws_a": ws_a,
        "ws_b": ws_b,
    }


# ============================================================================ #
# 1. Repository-level tests: Monotonic sequencing & event logging
# ============================================================================ #

async def test_repo_create_and_get_conversation(db_session: AsyncSession, tenant_workspaces):
    repo = ConversationRepository(db_session)
    ws_a = tenant_workspaces["ws_a"]
    user_a = tenant_workspaces["user_a"]

    conv = await repo.create_conversation(
        workspace_id=ws_a.workspace_id,
        owner_id=user_a,
        title="Project Planning Session",
        metadata={"client": "test"}
    )

    assert conv.conversation_id is not None
    assert conv.workspace_id == ws_a.workspace_id
    assert conv.owner_id == user_a
    assert conv.title == "Project Planning Session"
    assert conv.status == "active"
    assert conv.last_turn_sequence == 0
    assert conv.metadata_ == {"client": "test"}

    fetched = await repo.get_conversation(ws_a.workspace_id, conv.conversation_id)
    assert fetched is not None
    assert fetched.conversation_id == conv.conversation_id
    assert fetched.title == "Project Planning Session"


async def test_repo_append_turn_monotonic_sequence(db_session: AsyncSession, tenant_workspaces):
    repo = ConversationRepository(db_session)
    ws_a = tenant_workspaces["ws_a"]
    user_a = tenant_workspaces["user_a"]

    conv = await repo.create_conversation(
        workspace_id=ws_a.workspace_id,
        owner_id=user_a,
        title="Sequencing Test"
    )

    # Allocate sequence and append 3 turns
    seq_1 = await repo.allocate_turn_sequence(conv.conversation_id)
    turn_1 = await repo.append_turn(
        workspace_id=ws_a.workspace_id,
        conversation_id=conv.conversation_id,
        owner_id=user_a,
        mode="ground",
        user_message="First question",
        sequence=seq_1
    )
    assert turn_1.sequence == 1

    seq_2 = await repo.allocate_turn_sequence(conv.conversation_id)
    turn_2 = await repo.append_turn(
        workspace_id=ws_a.workspace_id,
        conversation_id=conv.conversation_id,
        owner_id=user_a,
        mode="research",
        user_message="Second question",
        sequence=seq_2
    )
    assert turn_2.sequence == 2

    seq_3 = await repo.allocate_turn_sequence(conv.conversation_id)
    turn_3 = await repo.append_turn(
        workspace_id=ws_a.workspace_id,
        conversation_id=conv.conversation_id,
        owner_id=user_a,
        mode="ground",
        user_message="Third question",
        sequence=seq_3
    )
    assert turn_3.sequence == 3

    turns, total = await repo.list_turns(ws_a.workspace_id, conv.conversation_id)
    assert total == 3
    assert len(turns) == 3
    assert [t.sequence for t in turns] == [1, 2, 3]


async def test_repo_log_event_and_retrieve(db_session: AsyncSession, tenant_workspaces):
    repo = ConversationRepository(db_session)
    ws_a = tenant_workspaces["ws_a"]
    user_a = tenant_workspaces["user_a"]

    conv = await repo.create_conversation(
        workspace_id=ws_a.workspace_id,
        owner_id=user_a,
        title="Events Test"
    )
    seq = await repo.allocate_turn_sequence(conv.conversation_id)
    turn = await repo.append_turn(
        workspace_id=ws_a.workspace_id,
        conversation_id=conv.conversation_id,
        owner_id=user_a,
        mode="ground",
        user_message="Hello",
        sequence=seq
    )

    ev1 = await repo.append_event(
        turn_id=turn.turn_id,
        sequence=1,
        event_type="text_delta",
        payload={"text": "Hello world"}
    )
    ev2 = await repo.append_event(
        turn_id=turn.turn_id,
        sequence=2,
        event_type="done",
        payload={"finish_reason": "stop"}
    )

    assert ev1.event_id is not None
    assert ev2.event_id is not None

    events = await repo.list_events_after(turn.turn_id, after_sequence=0)
    assert len(events) == 2
    assert events[0].event_type == "text_delta"
    assert events[1].event_type == "done"


# ============================================================================ #
# 2. REST API & Tenant Isolation Tests
# ============================================================================ #

async def test_api_create_conversation(tenant_workspaces):
    user_a = tenant_workspaces["user_a"]
    ws_a = tenant_workspaces["ws_a"]

    app.dependency_overrides[get_current_user] = lambda: user_a
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                f"/api/v1/workspaces/{ws_a.workspace_id}/conversations",
                json={"title": "API Test Conversation", "metadata": {"tag": "unit-test"}}
            )
            assert resp.status_code == 201, resp.text
            data = resp.json()
            assert data["title"] == "API Test Conversation"
            assert data["workspace_id"] == str(ws_a.workspace_id)
            assert data["owner_id"] == str(user_a)
            assert data["status"] == "active"
            assert data["last_turn_sequence"] == 0
            assert data["metadata"] == {"tag": "unit-test"}
    finally:
        app.dependency_overrides.pop(get_current_user, None)


async def test_api_list_and_filter_conversations(tenant_workspaces):
    user_a = tenant_workspaces["user_a"]
    ws_a = tenant_workspaces["ws_a"]

    app.dependency_overrides[get_current_user] = lambda: user_a
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Create two conversations
            c1_resp = await client.post(
                f"/api/v1/workspaces/{ws_a.workspace_id}/conversations",
                json={"title": "Conv Active 1"}
            )
            c2_resp = await client.post(
                f"/api/v1/workspaces/{ws_a.workspace_id}/conversations",
                json={"title": "Conv Active 2"}
            )
            c1_id = c1_resp.json()["conversation_id"]

            # Archive the first one
            patch_resp = await client.patch(
                f"/api/v1/workspaces/{ws_a.workspace_id}/conversations/{c1_id}",
                json={"status": "archived"}
            )
            assert patch_resp.status_code == 200
            assert patch_resp.json()["status"] == "archived"

            # Query active conversations (default filter)
            list_active = await client.get(
                f"/api/v1/workspaces/{ws_a.workspace_id}/conversations?status=active"
            )
            assert list_active.status_code == 200
            active_ids = [c["conversation_id"] for c in list_active.json()["conversations"]]
            assert c1_id not in active_ids

            # Query archived conversations
            list_archived = await client.get(
                f"/api/v1/workspaces/{ws_a.workspace_id}/conversations?status=archived"
            )
            assert list_archived.status_code == 200
            archived_ids = [c["conversation_id"] for c in list_archived.json()["conversations"]]
            assert c1_id in archived_ids
    finally:
        app.dependency_overrides.pop(get_current_user, None)


async def test_api_tenant_isolation_cross_user_rejection(tenant_workspaces):
    user_a = tenant_workspaces["user_a"]
    user_b = tenant_workspaces["user_b"]
    ws_a = tenant_workspaces["ws_a"]

    # User A creates a conversation
    app.dependency_overrides[get_current_user] = lambda: user_a
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                f"/api/v1/workspaces/{ws_a.workspace_id}/conversations",
                json={"title": "Secret Conversation of User A"}
            )
            assert resp.status_code == 201
            conv_id = resp.json()["conversation_id"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    # User B attempts to access User A's workspace conversation -> Expect 404
    app.dependency_overrides[get_current_user] = lambda: user_b
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Attempt to list conversations in User A's workspace
            list_resp = await client.get(
                f"/api/v1/workspaces/{ws_a.workspace_id}/conversations"
            )
            assert list_resp.status_code == 404

            # Attempt to get User A's specific conversation
            get_resp = await client.get(
                f"/api/v1/workspaces/{ws_a.workspace_id}/conversations/{conv_id}"
            )
            assert get_resp.status_code == 404

            # Attempt to modify User A's conversation
            patch_resp = await client.patch(
                f"/api/v1/workspaces/{ws_a.workspace_id}/conversations/{conv_id}",
                json={"title": "Hacked Title"}
            )
            assert patch_resp.status_code == 404
    finally:
        app.dependency_overrides.pop(get_current_user, None)
