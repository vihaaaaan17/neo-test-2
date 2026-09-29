import uuid
from typing import Optional, List, Tuple, Dict, Any
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.conversation import Conversation, ConversationTurn, ChatEvent


class ConversationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_conversation(
        self,
        workspace_id: UUID,
        owner_id: UUID,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Conversation:
        conversation = Conversation(
            workspace_id=workspace_id,
            owner_id=owner_id,
            title=title,
            metadata_=metadata or {}
        )
        self.session.add(conversation)
        await self.session.commit()
        await self.session.refresh(conversation)
        return conversation

    async def get_conversation(
        self,
        workspace_id: UUID,
        conversation_id: UUID
    ) -> Optional[Conversation]:
        stmt = select(Conversation).where(
            Conversation.workspace_id == workspace_id,
            Conversation.conversation_id == conversation_id
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_conversations(
        self,
        workspace_id: UUID,
        owner_id: Optional[UUID] = None,
        status: Optional[str] = "active",
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Conversation], int]:
        filters = [Conversation.workspace_id == workspace_id]
        if owner_id:
            filters.append(Conversation.owner_id == owner_id)
        if status:
            filters.append(Conversation.status == status)

        count_stmt = select(func.count(Conversation.conversation_id)).where(*filters)
        count_res = await self.session.execute(count_stmt)
        total = count_res.scalar_one()

        stmt = (
            select(Conversation)
            .where(*filters)
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def update_conversation(
        self,
        workspace_id: UUID,
        conversation_id: UUID,
        title: Optional[str] = None,
        status: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Conversation]:
        conversation = await self.get_conversation(workspace_id, conversation_id)
        if not conversation:
            return None

        if title is not None:
            conversation.title = title
        if status is not None:
            conversation.status = status
        if metadata is not None:
            conversation.metadata_ = metadata

        conversation.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(conversation)
        return conversation

    async def lock_conversation(self, conversation_id: UUID) -> Optional[Conversation]:
        """
        Row-locks the conversation using SELECT ... FOR UPDATE to serialize turn submissions.
        """
        stmt = (
            select(Conversation)
            .where(Conversation.conversation_id == conversation_id)
            .with_for_update()
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_active_turn(self, conversation_id: UUID) -> Optional[ConversationTurn]:
        """
        Returns any active turn in 'pending' or 'running' state for the conversation.
        """
        stmt = (
            select(ConversationTurn)
            .where(
                ConversationTurn.conversation_id == conversation_id,
                ConversationTurn.status.in_(["pending", "running"])
            )
            .order_by(ConversationTurn.sequence.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def allocate_turn_sequence(self, conversation_id: UUID) -> int:
        """
        Atomically increments and returns the next turn sequence number
        for a conversation using row-level locking (SELECT ... FOR UPDATE).
        """
        stmt = (
            select(Conversation)
            .where(Conversation.conversation_id == conversation_id)
            .with_for_update()
        )
        result = await self.session.execute(stmt)
        conv = result.scalars().first()
        if not conv:
            raise ValueError(f"Conversation {conversation_id} not found")

        next_sequence = conv.last_turn_sequence + 1
        conv.last_turn_sequence = next_sequence
        conv.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return next_sequence

    async def append_turn(
        self,
        workspace_id: UUID,
        conversation_id: UUID,
        owner_id: UUID,
        mode: str,
        user_message: str,
        sequence: int,
        client_request_id: Optional[str] = None,
        source_scope: Optional[List[UUID]] = None,
        context_version: Optional[Dict[str, Any]] = None
    ) -> ConversationTurn:
        turn = ConversationTurn(
            conversation_id=conversation_id,
            workspace_id=workspace_id,
            owner_id=owner_id,
            sequence=sequence,
            mode=mode,
            user_message=user_message,
            client_request_id=client_request_id,
            source_scope=[str(s) for s in source_scope] if source_scope else None,
            context_version=context_version or {},
            status="pending"
        )
        self.session.add(turn)
        await self.session.commit()
        await self.session.refresh(turn)
        return turn

    async def get_turn(
        self,
        workspace_id: UUID,
        conversation_id: UUID,
        turn_id: UUID
    ) -> Optional[ConversationTurn]:
        stmt = select(ConversationTurn).where(
            ConversationTurn.workspace_id == workspace_id,
            ConversationTurn.conversation_id == conversation_id,
            ConversationTurn.turn_id == turn_id
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_turn_by_client_request_id(
        self,
        conversation_id: UUID,
        client_request_id: str
    ) -> Optional[ConversationTurn]:
        stmt = select(ConversationTurn).where(
            ConversationTurn.conversation_id == conversation_id,
            ConversationTurn.client_request_id == client_request_id
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_turns(
        self,
        workspace_id: UUID,
        conversation_id: UUID,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[ConversationTurn], int]:
        filters = [
            ConversationTurn.workspace_id == workspace_id,
            ConversationTurn.conversation_id == conversation_id
        ]
        count_stmt = select(func.count(ConversationTurn.turn_id)).where(*filters)
        count_res = await self.session.execute(count_stmt)
        total = count_res.scalar_one()

        stmt = (
            select(ConversationTurn)
            .where(*filters)
            .order_by(ConversationTurn.sequence.asc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def set_turn_status(
        self,
        turn_id: UUID,
        status: str,
        expected_statuses: Optional[List[str]] = None,
        assistant_message: Optional[str] = None,
        ground_evidence_refs: Optional[List[Any]] = None,
        research_run_id: Optional[UUID] = None,
        context_version: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None
    ) -> Optional[ConversationTurn]:
        """
        Atomically updates turn status and attributes.
        When expected_statuses is provided, uses atomic Compare-And-Swap (CAS):
        UPDATE conversation_turns SET ... WHERE turn_id = :id AND status IN (:expected_statuses)
        """
        where_clauses = [ConversationTurn.turn_id == turn_id]
        if expected_statuses is not None:
            where_clauses.append(ConversationTurn.status.in_(expected_statuses))

        values: Dict[str, Any] = {"status": status}
        if assistant_message is not None:
            values["assistant_message"] = assistant_message
        if ground_evidence_refs is not None:
            values["ground_evidence_refs"] = ground_evidence_refs
        if research_run_id is not None:
            values["research_run_id"] = research_run_id
        if context_version is not None:
            values["context_version"] = context_version
        if error_code is not None:
            values["error_code"] = error_code
        if error_message is not None:
            values["error_message"] = error_message
        if started_at is not None:
            values["started_at"] = started_at
        if completed_at is not None:
            values["completed_at"] = completed_at

        stmt = (
            update(ConversationTurn)
            .where(*where_clauses)
            .values(**values)
            .returning(ConversationTurn)
        )
        result = await self.session.execute(stmt)
        turn = result.scalars().first()
        await self.session.commit()
        return turn

    async def set_turn_status_cas(
        self,
        turn_id: UUID,
        status: str,
        expected_statuses: Optional[List[str]] = None,
        **kwargs
    ) -> Optional[ConversationTurn]:
        """
        Atomic Compare-And-Swap (CAS) update helper:
        UPDATE conversation_turns SET status = :status WHERE turn_id = :turn_id AND status IN (:expected_statuses)
        """
        allowed = expected_statuses if expected_statuses is not None else ["pending", "running"]
        return await self.set_turn_status(
            turn_id=turn_id,
            status=status,
            expected_statuses=allowed,
            **kwargs
        )

    async def append_event(
        self,
        turn_id: UUID,
        sequence: int,
        event_type: str,
        payload: Optional[Dict[str, Any]] = None
    ) -> ChatEvent:
        event = ChatEvent(
            turn_id=turn_id,
            sequence=sequence,
            event_type=event_type,
            payload=payload or {}
        )
        self.session.add(event)
        await self.session.commit()
        await self.session.refresh(event)
        return event

    async def list_events_after(
        self,
        turn_id: UUID,
        after_sequence: int = 0
    ) -> List[ChatEvent]:
        stmt = (
            select(ChatEvent)
            .where(
                ChatEvent.turn_id == turn_id,
                ChatEvent.sequence > after_sequence
            )
            .order_by(ChatEvent.sequence.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
