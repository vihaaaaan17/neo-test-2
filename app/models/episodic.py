import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, ForeignKey, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base

class EpisodicMemory(Base):
    __tablename__ = "episodic_memories"

    episode_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.workspace_id", ondelete="CASCADE"), nullable=False)
    owner_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    event_type = Column(String, nullable=False)
    summary = Column(Text, nullable=False)
    importance = Column(Float, nullable=True)
    
    run_id = Column(UUID(as_uuid=True), nullable=True)
    task_id = Column(UUID(as_uuid=True), nullable=True)
    outcome = Column(String, nullable=True)
    entities = Column(JSONB, nullable=True)
    embedding_ref = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    workspace = relationship("Workspace")
