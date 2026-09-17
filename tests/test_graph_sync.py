import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.workers.tasks import sync_knowledge_to_graph_job
from app.models.knowledge import KnowledgeMemory
from app.models.workspace import Workspace
from app.core.database import async_session_maker
from app.repositories.graph import graph_store

@pytest.mark.asyncio
@pytest.mark.integration
async def test_sync_knowledge_to_graph_job():
    owner_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    knowledge_id = uuid.uuid4()
    
    # Insert dummy knowledge memory into postgres
    async with async_session_maker() as session:
        ws = Workspace(workspace_id=workspace_id, owner_id=owner_id)
        session.add(ws)
        await session.commit()
        
        mem = KnowledgeMemory(
            knowledge_id=knowledge_id,
            owner_id=owner_id,
            workspace_id=workspace_id,
            knowledge_type="finding",
            content="Sync test finding",
            status="verified",
            provenance={"source_refs": [], "source_mode": "research"},
            domain="test",
            version=1
        )
        session.add(mem)
        await session.commit()
    
    # Run the worker job
    result = await sync_knowledge_to_graph_job({}, knowledge_id=str(knowledge_id))
    
    assert result["status"] == "completed"
    assert result["knowledge_id"] == str(knowledge_id)
    
    # Query Neo4j to verify the node was created
    await graph_store.connect()
    query = """
    MATCH (w:Workspace {id: $workspace_id})-[:CONTAINS]->(k:Knowledge {id: $knowledge_id})
    RETURN k.content AS content, k.type AS type, k.domain AS domain
    """
    records = await graph_store.execute_query(query, {
        "workspace_id": str(workspace_id),
        "knowledge_id": str(knowledge_id)
    })
    
    assert len(records) == 1
    assert records[0]["content"] == "Sync test finding"
    assert records[0]["type"] == "finding"
    assert records[0]["domain"] == "test"
    
    # Verify idempotency by running again
    result2 = await sync_knowledge_to_graph_job({}, knowledge_id=str(knowledge_id))
    assert result2["status"] == "completed"
    
    records2 = await graph_store.execute_query(query, {
        "workspace_id": str(workspace_id),
        "knowledge_id": str(knowledge_id)
    })
    
    assert len(records2) == 1  # Should not duplicate
