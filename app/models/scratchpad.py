import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base


class ScratchpadEntry(Base):
    """
    First-class, durable PostgreSQL working-state record within a Neosis workspace.
    Represents interactive reasoning artifacts (notes, observations, hypotheses, investigations, findings).
    Scoped to conversation by default, but can be elevated across the workspace via pinning.
    """
    __tablename__ = "scratchpad_entries"

    entry_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.workspace_id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.conversation_id", ondelete="CASCADE"), nullable=True, index=True)
    turn_id = Column(UUID(as_uuid=True), ForeignKey("conversation_turns.turn_id", ondelete="SET NULL"), nullable=True, index=True)
    run_id = Column(UUID(as_uuid=True), ForeignKey("research_runs.run_id", ondelete="SET NULL"), nullable=True, index=True)

    entry_type = Column(String(32), nullable=False)  # "note", "observation", "hypothesis", "investigation", "finding"
    lifecycle = Column(String(32), default="active", nullable=False)  # "active", "promoted", "dismissed", "superseded"
    content = Column(Text, nullable=False)

    is_pinned_to_workspace = Column(Boolean, default=False, nullable=False, index=True)
    pinned_at = Column(DateTime(timezone=True), nullable=True)

    superseded_by_id = Column(UUID(as_uuid=True), ForeignKey("scratchpad_entries.entry_id", ondelete="SET NULL"), nullable=True)
    metadata_ = Column("metadata", JSONB, default=dict, nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    workspace = relationship("Workspace")
    conversation = relationship("Conversation")
    turn = relationship("ConversationTurn")
    run = relationship("ResearchRun")
    superseded_by = relationship("ScratchpadEntry", remote_side=[entry_id])

    __table_args__ = (
        Index("ix_scratchpad_workspace_lifecycle", "workspace_id", "lifecycle"),
        Index("ix_scratchpad_conversation_lifecycle", "conversation_id", "lifecycle"),
        Index("ix_scratchpad_workspace_pinned", "workspace_id", "is_pinned_to_workspace"),
    )
