import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, BigInteger, Integer, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base

class GroundConversation(Base):
    __tablename__ = "ground_conversations"

    conversation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.workspace_id", ondelete="CASCADE"), nullable=False, index=True)
    owner_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class Conversation(Base):
    """
    Canonical conversational container within a Neosis workspace.
    Mode-agnostic: individual turns within the conversation can alternate
    between 'ground' and 'research'.
    """
    __tablename__ = "conversations"

    conversation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.workspace_id", ondelete="CASCADE"), nullable=False, index=True)
    owner_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    title = Column(String(255), nullable=True)
    status = Column(String(32), default="active", nullable=False)  # "active", "archived"
    last_turn_sequence = Column(BigInteger, default=0, nullable=False)
    metadata_ = Column("metadata", JSONB, default=dict, nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    turns = relationship(
        "ConversationTurn",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ConversationTurn.sequence"
    )

    open_notebook_binding = relationship(
        "OpenNotebookConversationBinding",
        back_populates="conversation",
        uselist=False,
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_conversations_workspace_updated", "workspace_id", updated_at.desc()),
        Index("ix_conversations_workspace_owner", "workspace_id", "owner_id"),
    )


class ConversationTurn(Base):
    """
    Canonical turn record representing a single prompt-response interaction
    within a conversation. Enforces mode execution and durable state tracking.
    """
    __tablename__ = "conversation_turns"

    turn_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.conversation_id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.workspace_id", ondelete="CASCADE"), nullable=False, index=True)
    owner_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    sequence = Column(BigInteger, nullable=False)
    mode = Column(String(32), nullable=False)  # "ground" or "research"
    user_message = Column(Text, nullable=False)
    assistant_message = Column(Text, nullable=True)
    status = Column(String(32), default="pending", nullable=False)  # "pending", "running", "completed", "partial", "failed", "cancelled"
    research_run_id = Column(UUID(as_uuid=True), ForeignKey("research_runs.run_id", ondelete="SET NULL"), nullable=True, index=True)
    client_request_id = Column(String(255), nullable=True)
    source_scope = Column(JSONB, nullable=True)
    ground_evidence_refs = Column(JSONB, default=list, nullable=False)
    context_version = Column(JSONB, default=dict, nullable=False)
    error_code = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    conversation = relationship("Conversation", back_populates="turns")
    events = relationship(
        "ChatEvent",
        back_populates="turn",
        cascade="all, delete-orphan",
        order_by="ChatEvent.sequence"
    )

    __table_args__ = (
        UniqueConstraint("conversation_id", "sequence", name="uq_conversation_turn_sequence"),
        UniqueConstraint("conversation_id", "client_request_id", name="uq_conversation_turn_client_request_id"),
        Index("ix_turns_workspace_conversation", "workspace_id", "conversation_id"),
    )


class ChatEvent(Base):
    """
    Durable event record for real-time turn execution streaming and reconnect replay.
    """
    __tablename__ = "chat_events"

    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    turn_id = Column(UUID(as_uuid=True), ForeignKey("conversation_turns.turn_id", ondelete="CASCADE"), nullable=False, index=True)
    sequence = Column(Integer, nullable=False)
    event_type = Column(String(64), nullable=False)  # "status_change", "token", "strategy", "citation", "progress", "error", "done"
    payload = Column(JSONB, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    turn = relationship("ConversationTurn", back_populates="events")

    __table_args__ = (
        UniqueConstraint("turn_id", "sequence", name="uq_chat_event_sequence"),
    )
