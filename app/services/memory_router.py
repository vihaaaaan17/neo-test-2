from uuid import UUID
from arq import ArqRedis
from app.repositories.knowledge import KnowledgeRepository
from app.schemas.knowledge import KnowledgeMemoryCreate
from app.models.knowledge import KnowledgeMemory
from app.services.quota import QuotaService

class MemoryRouter:
    def __init__(self, repository: KnowledgeRepository, quota: QuotaService | None = None, arq_pool: ArqRedis | None = None):
        self.repository = repository
        self.quota = quota
        self.arq_pool = arq_pool

    async def route_to_memory(self, owner_id: UUID, workspace_id: UUID, data: KnowledgeMemoryCreate) -> KnowledgeMemory:
        """
        Intercepts memory pushes, ensuring they are tagged correctly via schema validation,
        and delegates to the repository. Enqueues graph sync task if configured.
        """
        # Pydantic validation guarantees source_mode is strictly 'ground' or 'research'.
        # No extra validation needed because KnowledgeMemoryCreate handles it.
        if self.quota:
            await self.quota.check_knowledge_limit(workspace_id)
            
        memory = await self.repository.create_knowledge(
            owner_id=owner_id, 
            workspace_id=workspace_id, 
            data=data
        )

        if self.arq_pool:
            await self.arq_pool.enqueue_job("sync_knowledge_to_graph_job", knowledge_id=str(memory.knowledge_id))

        return memory

class MemoryRouterService:
    @staticmethod
    def estimate_tokens(text: str) -> int:
        # A simple heuristic for token counting: ~4 characters per token
        return len(text) // 4

    @staticmethod
    def build_context(items: list['MemoryItem'], token_budget: int) -> 'ContextBundle':
        from app.schemas.context import ContextBundle
        
        # Priority mapping: lower number means it is evicted FIRST
        priority_map = {
            "episodic": 1,
            "knowledge": 2,
            "source": 3,
            "working": 4
        }

        # Calculate initial tokens
        for item in items:
            item._estimated_tokens = MemoryRouterService.estimate_tokens(item.text)

        total_tokens = sum(getattr(item, "_estimated_tokens", 0) for item in items)
        
        if total_tokens <= token_budget:
            return ContextBundle(budget=token_budget, total_tokens=total_tokens, items=items, evicted_items=[])

        # We need to evict items. Sort items by priority (lowest priority first to drop).
        # To make it deterministic for same priority, we could sort by size or id, let's sort by id as tiebreaker.
        sorted_items = sorted(items, key=lambda x: (priority_map.get(x.type, 0), x.id))

        evicted = []
        kept = []
        
        # We process from lowest priority (Episodic) to highest priority (Working)
        for item in sorted_items:
            if total_tokens > token_budget and item.type != "working":
                # We can evict this item
                total_tokens -= getattr(item, "_estimated_tokens", 0)
                evicted.append(item)
            else:
                # Keep it
                kept.append(item)

        # Working memory is preserved even if budget is exceeded, per spec.
        # But if we must drop working memory to fit, the spec says "preserved at all costs", 
        # so we will keep working memory even if total_tokens > token_budget.
        
        # Return the bundle with kept items in their original relative order
        kept_ids = {item.id for item in kept}
        final_items = [item for item in items if item.id in kept_ids]

        return ContextBundle(budget=token_budget, total_tokens=total_tokens, items=final_items, evicted_items=evicted)
