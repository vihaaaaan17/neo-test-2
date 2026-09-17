import uuid
from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base

class DocumentBlock(Base):
    __tablename__ = "document_blocks"

    block_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.source_id", ondelete="CASCADE"), nullable=False)
    snapshot_id = Column(UUID(as_uuid=True), ForeignKey("source_snapshots.snapshot_id", ondelete="CASCADE"), nullable=False)
    block_type = Column(String, nullable=False)
    sequence = Column(Integer, nullable=False)
    text_or_ref = Column(String, nullable=False)
    page_number = Column(Integer, nullable=True)
    metadata_ = Column(JSONB, nullable=True)

    source = relationship("Source")
    snapshot = relationship("SourceSnapshot")
