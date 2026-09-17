from uuid import UUID
from app.repositories.knowledge import KnowledgeRepository
from app.schemas.knowledge import KnowledgeMemoryCreate
from app.models.knowledge import KnowledgeMemory
from app.services.quota import QuotaService

class MemoryRouter:
    def __init__(self, repository: KnowledgeRepository, quota: QuotaService | None = None):
        self.repository = repository
        self.quota = quota

    async def route_to_memory(self, owner_id: UUID, workspace_id: UUID, data: KnowledgeMemoryCreate) -> KnowledgeMemory:
        """
        Intercepts memory pushes, ensuring they are tagged correctly via schema validation,
        and delegates to the repository.
        """
        # Pydantic validation guarantees source_mode is strictly 'ground' or 'research'.
        # No extra validation needed because KnowledgeMemoryCreate handles it.
        if self.quota:
            await self.quota.check_knowledge_limit(workspace_id)
            
        return await self.repository.create_knowledge(
            owner_id=owner_id, 
            workspace_id=workspace_id, 
            data=data
        )
