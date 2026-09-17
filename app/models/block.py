import uuid
from sqlalchemy import Column, String, Integer, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, TSVECTOR
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
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
    embedding = Column(Vector(768), nullable=True)
    search_vector = Column(TSVECTOR, nullable=True)

    source = relationship("Source")
    snapshot = relationship("SourceSnapshot")

    __table_args__ = (
        Index("ix_document_blocks_embedding", "embedding", postgresql_using="hnsw", postgresql_with={"m": 16, "ef_construction": 64}, postgresql_ops={'embedding': 'vector_cosine_ops'}),
        Index("ix_document_blocks_search_vector", "search_vector", postgresql_using="gin"),
        Index("ix_document_blocks_source_id", "source_id"),
    )
