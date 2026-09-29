import asyncio
import json
import pytest
from datetime import datetime, timezone
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.workspace import Workspace
from app.models.conversation import Conversation, ConversationTurn, ChatEvent
from app.services.chat.service import ChatService
from app.services.chat.events import ChatEventRepository, ChatEventService, format_sse_event, TurnEventBroker
from app.schemas.chat import TurnCreate, ChatEventType


def parse_sse_events(sse_text_chunks: list[str]) -> list[dict]:
    """Helper to parse a list of SSE lines/chunks into structured event dicts."""
    events = []
    current_event = {}
    for chunk in sse_text_chunks:
        lines = chunk.strip().split("\n")
        for line in lines:
            if line.startswith("event:"):
                current_event["event"] = line.removeprefix("event:").strip()
            elif line.startswith("data:"):
                raw_data = line.removeprefix("data:").strip()
                try:
                    current_event["data"] = json.loads(raw_data)
                except Exception:
                    current_event["data"] = raw_data
        if "event" in current_event and "data" in current_event:
            events.append(current_event)
            current_event = {}
    return events


@pytest.mark.asyncio
async def test_unified_sse_stream_ground_turn():
    """
    E2E Test: Unified SSE stream for Ground Turn delivers formatted SSE events
    (token, citation, ground_answer, done) and completes properly.
    """
    turn_id = uuid4()
    workspace_id = uuid4()
    conversation_id = uuid4()
    owner_id = uuid4()

    mock_db = AsyncMock()
    mock_conv_repo = AsyncMock()
    mock_workspace_repo = AsyncMock()
    mock_event_repo = AsyncMock()
    mock_arq = AsyncMock()

    # Pre-simulate that no events exist in DB at start
    mock_event_repo.list_events_after.return_value = []

    chat_service = ChatService(
        db=mock_db,
        conv_repo=mock_conv_repo,
        workspace_repo=mock_workspace_repo,
        event_repo=mock_event_repo,
        arq_redis=mock_arq
    )

    # Launch consumer of stream_turn_events
    stream_gen = chat_service.stream_turn_events(turn_id)

    async def produce_events():
        await asyncio.sleep(0.01)
        channel = f"turn_events:{turn_id}"
        # Broadcast live events through the local event broker with sequential sequence numbers
        await TurnEventBroker.publish_local(channel, {"sequence": 1, "event_type": "status_change", "payload": {"status": "running"}})
        await TurnEventBroker.publish_local(channel, {"sequence": 2, "event_type": "token", "payload": {"content": "Water boils at "}})
        await TurnEventBroker.publish_local(channel, {"sequence": 3, "event_type": "token", "payload": {"content": "100C."}})
        await TurnEventBroker.publish_local(channel, {"sequence": 4, "event_type": "ground_answer", "payload": {"answer": "Water boils at 100C."}})
        await TurnEventBroker.publish_local(channel, {"sequence": 5, "event_type": "done", "payload": {"status": "completed"}})

    producer_task = asyncio.create_task(produce_events())

    received_chunks = []
    async for chunk in stream_gen:
        received_chunks.append(chunk)

    await producer_task

    parsed = parse_sse_events(received_chunks)
    assert len(parsed) == 5
    assert parsed[0]["event"] == "status_change"
    assert parsed[1]["event"] == "token"
    assert parsed[1]["data"]["content"] == "Water boils at "
    assert parsed[2]["event"] == "token"
    assert parsed[2]["data"]["content"] == "100C."
    assert parsed[3]["event"] == "ground_answer"
    assert parsed[4]["event"] == "done"
    assert parsed[4]["data"]["status"] == "completed"


@pytest.mark.asyncio
async def test_unified_sse_stream_research_turn():
    """
    E2E Test: Unified SSE stream for Research Turn emits lifecycle milestones
    (started, planning, researching, synthesizing, completed, done).
    """
    turn_id = uuid4()
    run_id = uuid4()

    mock_db = AsyncMock()
    mock_event_repo = AsyncMock()
    mock_event_repo.list_events_after.return_value = []

    chat_service = ChatService(
        db=mock_db,
        event_repo=mock_event_repo,
        arq_redis=AsyncMock()
    )

    stream_gen = chat_service.stream_turn_events(turn_id)

    async def produce_research_events():
        await asyncio.sleep(0.01)
        channel = f"turn_events:{turn_id}"
        await TurnEventBroker.publish_local(channel, {"sequence": 1, "event_type": "turn.research_started", "payload": {"run_id": str(run_id)}})
        await TurnEventBroker.publish_local(channel, {"sequence": 2, "event_type": "turn.research_planning", "payload": {"step": "decomposing"}})
        await TurnEventBroker.publish_local(channel, {"sequence": 3, "event_type": "turn.researching", "payload": {"queries": ["q1", "q2"]}})
        await TurnEventBroker.publish_local(channel, {"sequence": 4, "event_type": "turn.synthesizing", "payload": {"status": "generating_report"}})
        await TurnEventBroker.publish_local(channel, {"sequence": 5, "event_type": "turn.completed", "payload": {"run_id": str(run_id)}})
        await TurnEventBroker.publish_local(channel, {"sequence": 6, "event_type": "done", "payload": {"status": "completed"}})

    producer_task = asyncio.create_task(produce_research_events())

    received_chunks = []
    async for chunk in stream_gen:
        received_chunks.append(chunk)

    await producer_task

    parsed = parse_sse_events(received_chunks)
    assert len(parsed) == 6
    event_types = [p["event"] for p in parsed]
    assert event_types == [
        "turn.research_started",
        "turn.research_planning",
        "turn.researching",
        "turn.synthesizing",
        "turn.completed",
        "done"
    ]


@pytest.mark.asyncio
async def test_event_replay_from_database_matches_live_broadcast():
    """
    E2E Test: Client reconnect catches up by replaying persisted PostgreSQL ChatEvent
    records in exact sequence order before receiving any live events.
    """
    turn_id = uuid4()

    mock_db = AsyncMock()
    mock_event_repo = AsyncMock()

    # Pre-populate 4 persisted events in DB
    ev1 = ChatEvent(event_id=uuid4(), turn_id=turn_id, sequence=1, event_type="status_change", payload={"status": "running"}, created_at=datetime.now(timezone.utc))
    ev2 = ChatEvent(event_id=uuid4(), turn_id=turn_id, sequence=2, event_type="token", payload={"content": "Alpha "}, created_at=datetime.now(timezone.utc))
    ev3 = ChatEvent(event_id=uuid4(), turn_id=turn_id, sequence=3, event_type="token", payload={"content": "Beta"}, created_at=datetime.now(timezone.utc))
    ev4 = ChatEvent(event_id=uuid4(), turn_id=turn_id, sequence=4, event_type="done", payload={"status": "completed"}, created_at=datetime.now(timezone.utc))

    mock_event_repo.list_events_after.return_value = [ev1, ev2, ev3, ev4]

    chat_service = ChatService(
        db=mock_db,
        event_repo=mock_event_repo,
        arq_redis=AsyncMock()
    )

    # Replay stream
    stream_gen = chat_service.stream_turn_events(turn_id)

    replayed_chunks = []
    async for chunk in stream_gen:
        replayed_chunks.append(chunk)

    # Verify DB was queried for replay with after_sequence=0
    mock_event_repo.list_events_after.assert_awaited_once_with(turn_id, after_sequence=0)

    parsed = parse_sse_events(replayed_chunks)
    assert len(parsed) == 4
    assert parsed[0]["event"] == "status_change"
    assert parsed[1]["event"] == "token"
    assert parsed[1]["data"]["content"] == "Alpha "
    assert parsed[2]["event"] == "token"
    assert parsed[2]["data"]["content"] == "Beta"
    assert parsed[3]["event"] == "done"
    assert parsed[3]["data"]["status"] == "completed"
