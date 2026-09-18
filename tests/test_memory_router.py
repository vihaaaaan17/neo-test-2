import pytest
from uuid import uuid4
from unittest.mock import AsyncMock
from pydantic import ValidationError
from app.services.memory_router import MemoryRouter, MemoryRouterService
from app.repositories.knowledge import KnowledgeRepository
from app.schemas.knowledge import KnowledgeMemoryCreate, Provenance
from app.models.knowledge import KnowledgeMemory
from app.schemas.context import MemoryItem, ContextBundle

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

def test_memory_router_service_no_eviction():
    items = [
        MemoryItem(id="1", type="source", text="This is a test source text.", metadata={}),
        MemoryItem(id="2", type="working", text="This is some working memory.", metadata={})
    ]
    # token budget 100 should easily fit everything
    bundle = MemoryRouterService.build_context(items, token_budget=100)
    assert len(bundle.items) == 2
    assert len(bundle.evicted_items) == 0
    assert bundle.total_tokens < 100

def test_memory_router_service_eviction_hierarchy():
    items = [
        MemoryItem(id="1", type="episodic", text="A"*40, metadata={}),
        MemoryItem(id="2", type="knowledge", text="B"*40, metadata={}),
        MemoryItem(id="3", type="source", text="C"*40, metadata={}),
        MemoryItem(id="4", type="working", text="D"*40, metadata={}),
    ]
    
    # Each item has ~10 tokens. 
    # Budget 25 -> Can fit 2 items. 
    bundle = MemoryRouterService.build_context(items, token_budget=25)
    
    assert len(bundle.items) == 2
    assert bundle.items[0].id == "3"
    assert bundle.items[1].id == "4"
    
    assert len(bundle.evicted_items) == 2
    evicted_ids = [i.id for i in bundle.evicted_items]
    assert "1" in evicted_ids # episodic
    assert "2" in evicted_ids # knowledge

def test_memory_router_preserves_working_memory_despite_budget():
    items = [
        MemoryItem(id="1", type="working", text="A"*40, metadata={}), # 10 tokens
        MemoryItem(id="2", type="working", text="B"*40, metadata={}), # 10 tokens
    ]
    
    # Budget is 5, but we cannot evict working memory!
    bundle = MemoryRouterService.build_context(items, token_budget=5)
    
    assert len(bundle.items) == 2
    assert len(bundle.evicted_items) == 0
    assert bundle.total_tokens == 20
