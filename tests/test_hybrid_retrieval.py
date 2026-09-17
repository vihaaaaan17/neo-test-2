import pytest
import pytest_asyncio
from uuid import uuid4
from app.services.hybrid_retrieval import HybridRetrievalService, RetrievedChunk
from app.core.database import engine
from sqlalchemy import text
import asyncio

# Mark all async tests
pytestmark = pytest.mark.asyncio

@pytest_asyncio.fixture
async def setup_test_data():
    workspace_id = uuid4()
    owner_id = uuid4()
    source_id = uuid4()
    snapshot_id = uuid4()

    async with engine.begin() as conn:
        # 1. Create workspace
        await conn.execute(
            text("INSERT INTO workspaces (workspace_id, owner_id, status, created_at, updated_at) VALUES (:w_id, :o_id, 'active', NOW(), NOW())"),
            {"w_id": workspace_id, "o_id": owner_id}
        )
        # 2. Create source
        await conn.execute(
            text("INSERT INTO sources (source_id, workspace_id, owner_id, source_type, processing_status, created_at, updated_at) VALUES (:s_id, :w_id, :o_id, 'document', 'completed', NOW(), NOW())"),
            {"s_id": source_id, "w_id": workspace_id, "o_id": owner_id}
        )
        # 3. Create snapshot
        await conn.execute(
            text("INSERT INTO source_snapshots (snapshot_id, source_id, file_uri, filename, size, checksum_sha256, created_at) VALUES (:snap_id, :s_id, 'uri', 'test.pdf', 100, 'hash', NOW())"),
            {"snap_id": snapshot_id, "s_id": source_id}
        )
        # 4. Create document blocks
        emb1 = [0.1] * 768
        emb2 = [0.9] * 768
        
        # Format the arrays as strings for Postgres insertion
        emb1_str = f"[{','.join(map(str, emb1))}]"
        emb2_str = f"[{','.join(map(str, emb2))}]"
        
        await conn.execute(
            text("""
                INSERT INTO document_blocks (block_id, source_id, snapshot_id, block_type, sequence, text_or_ref, embedding, search_vector) 
                VALUES 
                (:b1, :s_id, :snap_id, 'text', 1, 'This is a text about artificial intelligence.', CAST(:e1 AS vector), to_tsvector('english', 'This is a text about artificial intelligence.')),
                (:b2, :s_id, :snap_id, 'text', 2, 'Keyword specific completely different topic.', CAST(:e2 AS vector), to_tsvector('english', 'Keyword specific completely different topic.'))
            """),
            {
                "b1": uuid4(),
                "b2": uuid4(),
                "s_id": source_id,
                "snap_id": snapshot_id,
                "e1": emb1_str,
                "e2": emb2_str
            }
        )
    
    yield workspace_id
    
    # Teardown
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM workspaces WHERE workspace_id = :w_id"), {"w_id": workspace_id})

async def test_hybrid_retrieval(setup_test_data):
    workspace_id = setup_test_data
    service = HybridRetrievalService(top_k=5, rrf_k=60)
    
    query_text = "Keyword specific"
    # Query vector matches block 1 perfectly
    query_embedding = [0.1] * 768
    
    results = await service.retrieve(workspace_id, query_text, query_embedding)
    
    # RRF should combine both blocks, so we expect exactly 2 results returned.
    assert len(results) == 2
    assert isinstance(results[0], RetrievedChunk)
    assert results[0].score > 0
    assert results[1].score > 0
