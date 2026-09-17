import logging
from typing import List
from uuid import UUID
from sqlalchemy import text
from app.core.database import engine
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class RetrievedChunk(BaseModel):
    block_id: UUID
    text: str
    metadata: dict | None = None
    page_number: int | None = None
    source_id: UUID
    score: float

class HybridRetrievalService:
    def __init__(self, top_k: int = 5, rrf_k: int = 60):
        self.top_k = top_k
        self.rrf_k = rrf_k

    async def retrieve(
        self, 
        workspace_id: UUID, 
        query_text: str, 
        query_embedding: list[float]
    ) -> List[RetrievedChunk]:
        """
        Executes a Reciprocal Rank Fusion (RRF) search across keyword and vector similarities.
        Strictly scopes all queries to the given workspace_id.
        """
        # We use a raw SQL query since this complex CTE logic is difficult to represent in pure SQLAlchemy Core ORM,
        # and RRF across both pgvector and tsvector is most efficiently done in the database.
        
        sql = """
        WITH vector_search AS (
            SELECT 
                db.block_id, 
                db.embedding <=> CAST(:query_embedding AS vector) AS vector_score,
                row_number() OVER (ORDER BY db.embedding <=> CAST(:query_embedding AS vector)) as vector_rank
            FROM document_blocks db
            JOIN sources s ON db.source_id = s.source_id
            WHERE s.workspace_id = :workspace_id
            ORDER BY vector_score
            LIMIT :top_k
        ),
        text_search AS (
            SELECT 
                db.block_id, 
                ts_rank(db.search_vector, websearch_to_tsquery('english', :query_text)) AS text_score,
                row_number() OVER (ORDER BY ts_rank(db.search_vector, websearch_to_tsquery('english', :query_text)) DESC) as text_rank
            FROM document_blocks db
            JOIN sources s ON db.source_id = s.source_id
            WHERE s.workspace_id = :workspace_id
              AND db.search_vector @@ websearch_to_tsquery('english', :query_text)
            ORDER BY text_score DESC
            LIMIT :top_k
        )
        SELECT 
            db.block_id, 
            db.text_or_ref, 
            db.metadata_, 
            db.page_number, 
            db.source_id,
            COALESCE(1.0 / (:rrf_k + vs.vector_rank), 0.0) +
            COALESCE(1.0 / (:rrf_k + ts.text_rank), 0.0) AS rrf_score
        FROM document_blocks db
        LEFT JOIN vector_search vs ON db.block_id = vs.block_id
        LEFT JOIN text_search ts ON db.block_id = ts.block_id
        WHERE vs.block_id IS NOT NULL OR ts.block_id IS NOT NULL
        ORDER BY rrf_score DESC
        LIMIT :top_k;
        """

        query_embedding_str = f"[{','.join(map(str, query_embedding))}]"
        
        try:
            async with engine.connect() as conn:
                result = await conn.execute(
                    text(sql),
                    {
                        "workspace_id": workspace_id,
                        "query_text": query_text,
                        "query_embedding": query_embedding_str,
                        "top_k": self.top_k,
                        "rrf_k": self.rrf_k
                    }
                )
                
                chunks = []
                for row in result:
                    chunks.append(RetrievedChunk(
                        block_id=row.block_id,
                        text=row.text_or_ref,
                        metadata=row.metadata_,
                        page_number=row.page_number,
                        source_id=row.source_id,
                        score=row.rrf_score
                    ))
                    
                return chunks
        except Exception as e:
            logger.error(f"Hybrid retrieval failed for workspace {workspace_id}: {e}")
            raise
