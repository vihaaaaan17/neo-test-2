import json
import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime, timezone
import asyncio
import inspect

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.conversation import ChatEvent, ConversationTurn

logger = logging.getLogger(__name__)


def format_sse_event(event_type: str, data: Any) -> str:
    """
    Formats an event as standard Server-Sent Event (SSE):
    event: <event_type>\n
    data: <json_payload>\n\n
    """
    if isinstance(data, (dict, list)):
        payload_str = json.dumps(data)
    elif isinstance(data, str):
        try:
            # Check if already valid JSON string
            json.loads(data)
            payload_str = data
        except Exception:
            payload_str = json.dumps({"content": data})
    else:
        payload_str = json.dumps(data)

    return f"event: {event_type}\ndata: {payload_str}\n\n"


class ChatEventRepository:
    """
    Repository for atomic ChatEvent persistence with monotonic sequence allocation per turn.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def append_event(
        self,
        turn_id: UUID,
        event_type: str,
        payload: Optional[Dict[str, Any]] = None
    ) -> ChatEvent:
        """
        Atomically allocates the next monotonic sequence number for the turn
        and inserts the ChatEvent record.

        Uses SELECT FOR UPDATE on the parent ConversationTurn row to serialize
        concurrent callers and prevent duplicate sequence numbers that would
        violate the uq_chat_event_sequence unique constraint.
        """
        # Acquire a row-level lock on the parent turn to serialize concurrent
        # event appenders for this turn. This ensures MAX(sequence) reads are
        # serialized — no two sessions can proceed past this point simultaneously
        # for the same turn_id.
        lock_stmt = (
            select(ConversationTurn)
            .where(ConversationTurn.turn_id == turn_id)
            .with_for_update()
        )
        await self.session.execute(lock_stmt)

        stmt = (
            select(func.coalesce(func.max(ChatEvent.sequence), 0))
            .where(ChatEvent.turn_id == turn_id)
        )
        res = await self.session.execute(stmt)
        next_seq = (res.scalar() or 0) + 1

        event = ChatEvent(
            turn_id=turn_id,
            sequence=next_seq,
            event_type=event_type,
            payload=payload or {},
            created_at=datetime.now(timezone.utc)
        )
        add_res = self.session.add(event)
        if inspect.isawaitable(add_res):
            await add_res
        await self.session.commit()
        await self.session.refresh(event)
        if not getattr(event, "created_at", None):
            event.created_at = datetime.now(timezone.utc)
        return event

    async def list_events_after(
        self,
        turn_id: UUID,
        after_sequence: int = 0
    ) -> List[ChatEvent]:
        """
        Fetches all events for a given turn strictly after the specified sequence,
        ordered by sequence ascending.
        """
        stmt = (
            select(ChatEvent)
            .where(
                ChatEvent.turn_id == turn_id,
                ChatEvent.sequence > after_sequence
            )
            .order_by(ChatEvent.sequence.asc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())


class TurnEventBroker:
    """
    Dual in-process and Redis Pub/Sub event broker.
    Provides sub/pub abstraction for live SSE streaming.
    """
    _subscribers: Dict[str, List[asyncio.Queue]] = {}

    @classmethod
    def subscribe_local(cls, channel: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        if channel not in cls._subscribers:
            cls._subscribers[channel] = []
        cls._subscribers[channel].append(q)
        return q

    @classmethod
    def unsubscribe_local(cls, channel: str, q: asyncio.Queue):
        if channel in cls._subscribers:
            if q in cls._subscribers[channel]:
                cls._subscribers[channel].remove(q)
            if not cls._subscribers[channel]:
                del cls._subscribers[channel]

    @classmethod
    async def publish_local(cls, channel: str, message: Any):
        if channel in cls._subscribers:
            for q in list(cls._subscribers[channel]):
                await q.put(message)


class ChatEventService:
    """
    Service coordinating event recording into PostgreSQL and broadcast across
    local queues and Redis channels.
    """

    def __init__(self, repo: ChatEventRepository, redis_client: Optional[Any] = None):
        self.repo = repo
        self.redis_client = redis_client

    async def record_and_publish(
        self,
        turn_id: UUID,
        event_type: str,
        payload: Dict[str, Any]
    ) -> ChatEvent:
        """
        Atomically records the event in PostgreSQL and broadcasts it to both
        the in-process broker and the Redis channel.
        """
        event = await self.repo.append_event(turn_id, event_type, payload)
        ev_created_at = (
            event.created_at.isoformat()
            if getattr(event, "created_at", None)
            else datetime.now(timezone.utc).isoformat()
        )
        message = {
            "event_id": str(event.event_id),
            "turn_id": str(turn_id),
            "sequence": event.sequence,
            "event_type": event_type,
            "payload": payload,
            "created_at": ev_created_at
        }

        # 1. Local in-process broadcast
        await TurnEventBroker.publish_local(f"turn_events:{turn_id}", message)

        # 2. Redis broadcast if available
        if self.redis_client and hasattr(self.redis_client, "publish"):
            try:
                await self.redis_client.publish(f"turn_events:{turn_id}", json.dumps(message))
            except Exception as e:
                logger.warning(f"Failed to publish to Redis turn_events:{turn_id}: {e}")

        return event

    async def get_turn_events(
        self,
        turn_id: UUID,
        after_sequence: int = 0
    ) -> List[ChatEvent]:
        """
        Retrieves historical events for reconnect replay.
        """
        return await self.repo.list_events_after(turn_id, after_sequence)
