import pytest
from uuid import uuid4
from unittest.mock import AsyncMock
from pydantic import ValidationError
from app.services.memory_router import MemoryRouter
from app.repositories.knowledge import KnowledgeRepository
from app.schemas.knowledge import KnowledgeMemoryCreate, Provenance
from app.models.knowledge import KnowledgeMemory

@pytest.mark.asyncio
async def test_invalid_source_mode():
    repo = AsyncMock(spec=KnowledgeRepository)
    router = MemoryRouter(repository=repo)
    
    with pytest.raises(ValidationError):
        # Validation happens at Pydantic level before it even reaches the router
        Provenance(source_refs=[uuid4()], source_mode="invalid_mode")

@pytest.mark.asyncio
async def test_valid_routing_without_arq():
    repo = AsyncMock(spec=KnowledgeRepository)
    router = MemoryRouter(repository=repo)
    
    workspace_id = uuid4()
    owner_id = uuid4()
    
    mem = KnowledgeMemoryCreate(
        knowledge_type="finding",
        content="Test content",
        status="verified",
        provenance=Provenance(source_refs=[], source_mode="research")
    )
    
    expected_memory = KnowledgeMemory(knowledge_id=uuid4(), content="Test content")
    repo.create_knowledge.return_value = expected_memory
    
    result = await router.route_to_memory(owner_id, workspace_id, mem)
    
    assert result == expected_memory
    repo.create_knowledge.assert_called_once_with(
        owner_id=owner_id,
        workspace_id=workspace_id,
        data=mem
    )

@pytest.mark.asyncio
async def test_valid_routing_with_arq():
    repo = AsyncMock(spec=KnowledgeRepository)
    arq_pool = AsyncMock()
    router = MemoryRouter(repository=repo, arq_pool=arq_pool)
    
    workspace_id = uuid4()
    owner_id = uuid4()
    knowledge_id = uuid4()
    
    mem = KnowledgeMemoryCreate(
        knowledge_type="finding",
        content="Test content",
        status="verified",
        provenance=Provenance(source_refs=[], source_mode="research")
    )
    
    expected_memory = KnowledgeMemory(knowledge_id=knowledge_id, content="Test content")
    repo.create_knowledge.return_value = expected_memory
    
    result = await router.route_to_memory(owner_id, workspace_id, mem)
    
    assert result == expected_memory
    repo.create_knowledge.assert_called_once_with(
        owner_id=owner_id,
        workspace_id=workspace_id,
        data=mem
    )
    arq_pool.enqueue_job.assert_called_once_with("sync_knowledge_to_graph_job", knowledge_id=str(knowledge_id))
