import json
import uuid
from uuid import UUID
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update

from app.main import app
from app.core.database import async_session_maker
from app.models.workspace import Workspace
from app.models.conversation import Conversation, ConversationTurn, ChatEvent
from app.models.open_notebook_binding import OpenNotebookWorkspaceBinding
from app.models.research import ResearchRun
from app.api.deps.auth import get_current_user
from app.api.deps.arq import get_arq_redis
from app.services.chat.events import ChatEventRepository, TurnEventBroker, format_sse_event

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


@pytest_asyncio.fixture
async def db_session():
    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def test_env(db_session: AsyncSession):
    # Ensure active runs quota headroom
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
        self._published = []

    async def enqueue_job(self, function, *args, **kwargs):
        self.jobs.append((function, args, kwargs))

    async def publish(self, channel, message):
        self._published.append((channel, message))
        # Also mirror to local broker for tests
        raw = json.loads(message) if isinstance(message, str) else message
        await TurnEventBroker.publish_local(channel, raw)


def parse_sse_events(raw_text: str):
    """
    Helper to parse raw SSE chunks into list of dicts: {'event': ..., 'data': ...}
    """
    events = []
    current_event = "message"
    current_data = []

    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            if current_data:
                data_str = "\n".join(current_data)
                try:
                    parsed_payload = json.loads(data_str)
                except Exception:
                    parsed_payload = data_str
                events.append({"event": current_event, "data": parsed_payload})
                current_event = "message"
                current_data = []
        elif line.startswith("event: "):
            current_event = line[7:].strip()
        elif line.startswith("data: "):
            current_data.append(line[6:].strip())

    if current_data:
        data_str = "\n".join(current_data)
        try:
            parsed_payload = json.loads(data_str)
        except Exception:
            parsed_payload = data_str
        events.append({"event": current_event, "data": parsed_payload})

    return events


# ============================================================================ #
# 1. ChatEventRepository Monotonic Sequencing & Atomic Persistence
# ============================================================================ #

async def test_chat_event_repository_monotonic_sequencing(test_env, db_session: AsyncSession):
    ws_a = test_env["ws_a"]
    conv_a = test_env["conv_a"]

    # Create dummy turn
    turn = ConversationTurn(
        conversation_id=conv_a.conversation_id,
        workspace_id=ws_a.workspace_id,
        owner_id=conv_a.owner_id,
        sequence=1,
        mode="ground",
        user_message="Test prompt",
        status="running"
    )
    db_session.add(turn)
    await db_session.commit()
    await db_session.refresh(turn)

    repo = ChatEventRepository(db_session)

    # Append 3 sequential events
    ev1 = await repo.append_event(turn.turn_id, "status_change", {"status": "running"})
    ev2 = await repo.append_event(turn.turn_id, "token", {"content": "Hello"})
    ev3 = await repo.append_event(turn.turn_id, "done", {"status": "completed"})

    assert ev1.sequence == 1
    assert ev2.sequence == 2
    assert ev3.sequence == 3
    assert ev1.event_type == "status_change"
    assert ev2.event_type == "token"
    assert ev3.event_type == "done"

    # Test list_events_after filtering
    all_events = await repo.list_events_after(turn.turn_id, after_sequence=0)
    assert len(all_events) == 3
    assert [e.sequence for e in all_events] == [1, 2, 3]

    partial_events = await repo.list_events_after(turn.turn_id, after_sequence=1)
    assert len(partial_events) == 2
    assert [e.sequence for e in partial_events] == [2, 3]


# ============================================================================ #
# 2. Ground Turn SSE Streaming
# ============================================================================ #

async def test_ground_turn_sse_streaming(test_env, db_session: AsyncSession):
    user_a = test_env["user_a"]
    ws_a = test_env["ws_a"]
    conv_a = test_env["conv_a"]

    mock_redis = MockArqRedis()
    app.dependency_overrides[get_current_user] = lambda: user_a
    app.dependency_overrides[get_arq_redis] = lambda: mock_redis

    evidence_id = str(uuid.uuid4())

    async def mock_stream(session_id, notebook_id, message):
        yield {"event": "strategy", "data": {"reasoning": "analyzing sources...", "searches": ["specs"]}}
        yield {"event": "token", "data": {"token": "The "}}
        yield {"event": "token", "data": {"token": "architecture "}}
        yield {"event": "token", "data": {"token": "is sound."}}
        yield {"event": "citation", "data": {"evidence": [{"source_id": evidence_id, "title": "Spec"}]}}
        yield {"event": "done", "data": {"answer": "The architecture is sound.", "evidence": [{"source_id": evidence_id}]}}

    try:
        with patch("app.services.chat.service.OpenNotebookClient.create_chat_session", new_callable=AsyncMock) as mock_sess, \
             patch("app.services.chat.service.OpenNotebookClient.chat_stream", new_callable=MagicMock, side_effect=mock_stream):
            mock_sess.return_value = f"session:{uuid.uuid4()}"

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(
                    f"/api/v1/workspaces/{ws_a.workspace_id}/conversations/{conv_a.conversation_id}/turns?stream=true",
                    json={"message": "Analyze system architecture", "mode": "ground"}
                )

                assert resp.status_code == 200
                assert "text/event-stream" in resp.headers["content-type"]

                events = parse_sse_events(resp.text)
                assert len(events) >= 5

                event_types = [e["event"] for e in events]
                assert "status_change" in event_types
                assert "strategy" in event_types
                assert "token" in event_types
                assert "citation" in event_types
                assert "done" in event_types

                # Verify terminal done payload
                done_event = next(e for e in events if e["event"] == "done")
                assert done_event["data"]["status"] == "completed"
                assert "The architecture is sound." in done_event["data"]["assistant_message"]

                # Verify DB persistence
                repo = ChatEventRepository(db_session)
                turns = await client.get(f"/api/v1/workspaces/{ws_a.workspace_id}/conversations/{conv_a.conversation_id}/turns")
                turn_id = UUID(turns.json()["turns"][0]["turn_id"])

                db_events = await repo.list_events_after(turn_id, 0)
                assert len(db_events) >= 5
                # Verify strictly monotonic sequences
                seqs = [e.sequence for e in db_events]
                assert seqs == list(range(1, len(seqs) + 1))
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_arq_redis, None)


# ============================================================================ #
# 3. Research Turn SSE Streaming with Redis Pub/Sub Event Bridging
# ============================================================================ #

async def test_research_turn_sse_streaming_redis_bridge(test_env, db_session: AsyncSession):
    user_a = test_env["user_a"]
    ws_a = test_env["ws_a"]
    conv_a = test_env["conv_a"]

    mock_redis = MockArqRedis()
    app.dependency_overrides[get_current_user] = lambda: user_a
    app.dependency_overrides[get_arq_redis] = lambda: mock_redis

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # We will start the stream request in a background task
            async def run_stream():
                return await client.post(
                    f"/api/v1/workspaces/{ws_a.workspace_id}/conversations/{conv_a.conversation_id}/turns?stream=true",
                    json={"message": "Deep consensus investigation", "mode": "research"}
                )

            stream_task = asyncio.create_task(run_stream())

            # Wait for research job to be enqueued
            for _ in range(50):
                if mock_redis.jobs:
                    break
                await asyncio.sleep(0.05)
            assert len(mock_redis.jobs) == 1
            run_id = mock_redis.jobs[0][2]["run_id"]

            # Wait for subscriber to be ready
            channel = f"research_events:{run_id}"
            for _ in range(50):
                if channel in TurnEventBroker._subscribers:
                    break
                await asyncio.sleep(0.05)

            # Simulate worker publishing events to research_events:{run_id}
            await TurnEventBroker.publish_local(channel, {
                "event_type": "progress",
                "payload": {"stage": "searching", "step": 1}
            })
            await TurnEventBroker.publish_local(channel, {
                "event_type": "token",
                "payload": {"content": "Found 3 consensus models."}
            })
            await TurnEventBroker.publish_local(channel, {
                "event_type": "status_change",
                "payload": {"status": "completed"}
            })

            resp = await stream_task
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]

            events = parse_sse_events(resp.text)
            event_types = [e["event"] for e in events]
            assert "status_change" in event_types
            assert "progress" in event_types
            assert "token" in event_types
            assert "done" in event_types
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_arq_redis, None)


# ============================================================================ #
# 4. Client Disconnect Resilience
# ============================================================================ #

async def test_client_disconnect_does_not_abort_turn(test_env, db_session: AsyncSession):
    user_a = test_env["user_a"]
    ws_a = test_env["ws_a"]
    conv_a = test_env["conv_a"]

    app.dependency_overrides[get_current_user] = lambda: user_a

    async def slow_stream(session_id, notebook_id, message):
        yield {"event": "token", "data": {"token": "Part 1 "}}
        await asyncio.sleep(0.15)
        yield {"event": "token", "data": {"token": "Part 2."}}
        yield {"event": "done", "data": {"answer": "Part 1 Part 2.", "evidence": []}}

    try:
        with patch("app.services.chat.service.OpenNotebookClient.create_chat_session", new_callable=AsyncMock) as mock_sess, \
             patch("app.services.chat.service.OpenNotebookClient.chat_stream", new_callable=MagicMock, side_effect=slow_stream):
            mock_sess.return_value = f"session:{uuid.uuid4()}"

            # We use a custom transport or partial read to simulate early disconnect
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                async with client.stream(
                    "POST",
                    f"/api/v1/workspaces/{ws_a.workspace_id}/conversations/{conv_a.conversation_id}/turns?stream=true",
                    json={"message": "Long generation", "mode": "ground"}
                ) as response:
                    assert response.status_code == 200
                    # Read just the first chunk
                    async for line in response.aiter_lines():
                        if "status_change" in line:
                            # Immediately disconnect!
                            break

                # Give the detached background task time to complete in PostgreSQL
                await asyncio.sleep(0.4)

                # Verify that the turn in DB finished successfully
                turns_resp = await client.get(f"/api/v1/workspaces/{ws_a.workspace_id}/conversations/{conv_a.conversation_id}/turns")
                turn_data = turns_resp.json()["turns"][0]

                assert turn_data["status"] == "completed"
                assert "Part 1 Part 2." in turn_data["assistant_message"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)


# ============================================================================ #
# 5. Historical Replay Endpoint & after_sequence Filtering
# ============================================================================ #

async def test_replay_historical_events(test_env, db_session: AsyncSession):
    user_a = test_env["user_a"]
    ws_a = test_env["ws_a"]
    conv_a = test_env["conv_a"]

    app.dependency_overrides[get_current_user] = lambda: user_a

    # Create a turn with 4 events
    turn = ConversationTurn(
        conversation_id=conv_a.conversation_id,
        workspace_id=ws_a.workspace_id,
        owner_id=user_a,
        sequence=1,
        mode="ground",
        user_message="Test replay",
        status="completed"
    )
    db_session.add(turn)
    await db_session.commit()
    await db_session.refresh(turn)

    repo = ChatEventRepository(db_session)
    await repo.append_event(turn.turn_id, "status_change", {"status": "running"})
    await repo.append_event(turn.turn_id, "strategy", {"reasoning": "thought"})
    await repo.append_event(turn.turn_id, "token", {"content": "text"})
    await repo.append_event(turn.turn_id, "done", {"status": "completed"})

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. Fetch all events (default)
            resp_all = await client.get(
                f"/api/v1/workspaces/{ws_a.workspace_id}/conversations/{conv_a.conversation_id}/turns/{turn.turn_id}/events"
            )
            assert resp_all.status_code == 200
            data_all = resp_all.json()
            assert data_all["total"] == 4
            assert [e["sequence"] for e in data_all["events"]] == [1, 2, 3, 4]

            # 2. Fetch events after_sequence=2
            resp_after = await client.get(
                f"/api/v1/workspaces/{ws_a.workspace_id}/conversations/{conv_a.conversation_id}/turns/{turn.turn_id}/events?after_sequence=2"
            )
            assert resp_after.status_code == 200
            data_after = resp_after.json()
            assert data_after["total"] == 2
            assert [e["sequence"] for e in data_after["events"]] == [3, 4]

            # 3. Stream replay via SSE
            resp_stream = await client.get(
                f"/api/v1/workspaces/{ws_a.workspace_id}/conversations/{conv_a.conversation_id}/turns/{turn.turn_id}/events?stream=true&after_sequence=2"
            )
            assert resp_stream.status_code == 200
            assert "text/event-stream" in resp_stream.headers["content-type"]
            stream_events = parse_sse_events(resp_stream.text)
            assert len(stream_events) == 2
            assert stream_events[0]["event"] == "token"
            assert stream_events[1]["event"] == "done"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


# ============================================================================ #
# 6. Replay Multi-Tenant Isolation
# ============================================================================ #

async def test_replay_multi_tenant_isolation(test_env, db_session: AsyncSession):
    user_a = test_env["user_a"]
    user_b = test_env["user_b"]
    ws_a = test_env["ws_a"]
    ws_b = test_env["ws_b"]
    conv_a = test_env["conv_a"]

    # Turn belonging to user_a
    turn = ConversationTurn(
        conversation_id=conv_a.conversation_id,
        workspace_id=ws_a.workspace_id,
        owner_id=user_a,
        sequence=1,
        mode="ground",
        user_message="Private turn",
        status="completed"
    )
    db_session.add(turn)
    await db_session.commit()
    await db_session.refresh(turn)

    repo = ChatEventRepository(db_session)
    await repo.append_event(turn.turn_id, "token", {"content": "secret"})

    # Attempt access as user_b
    app.dependency_overrides[get_current_user] = lambda: user_b

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                f"/api/v1/workspaces/{ws_a.workspace_id}/conversations/{conv_a.conversation_id}/turns/{turn.turn_id}/events"
            )
            assert resp.status_code in [403, 404]

            # Cross-workspace mismatch
            resp_mismatch = await client.get(
                f"/api/v1/workspaces/{ws_b.workspace_id}/conversations/{conv_a.conversation_id}/turns/{turn.turn_id}/events"
            )
            assert resp_mismatch.status_code in [403, 404]
    finally:
        app.dependency_overrides.pop(get_current_user, None)
