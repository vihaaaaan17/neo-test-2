import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, ForeignKey, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base

class KnowledgeMemory(Base):
    __tablename__ = "knowledge_memories"

    knowledge_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.workspace_id", ondelete="CASCADE"), nullable=False)
    owner_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    knowledge_type = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    status = Column(String, nullable=False)
    provenance = Column(JSONB, nullable=False)
    
    confidence = Column(Float, nullable=True)
    tags = Column(JSONB, nullable=True)
    entities = Column(JSONB, nullable=True)
    domain = Column(String, nullable=True)
    version = Column(Integer, nullable=True, default=1)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    workspace = relationship("Workspace")
