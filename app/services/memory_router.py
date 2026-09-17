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
