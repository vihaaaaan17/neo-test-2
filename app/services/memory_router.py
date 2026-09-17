from uuid import UUID
from app.repositories.knowledge import KnowledgeRepository
from app.schemas.knowledge import KnowledgeMemoryCreate
from app.models.knowledge import KnowledgeMemory

class MemoryRouter:
    def __init__(self, repository: KnowledgeRepository):
        self.repository = repository

    async def route_to_memory(self, owner_id: UUID, workspace_id: UUID, data: KnowledgeMemoryCreate) -> KnowledgeMemory:
        """
        Intercepts memory pushes, ensuring they are tagged correctly via schema validation,
        and delegates to the repository.
        """
        # Pydantic validation guarantees source_mode is strictly 'ground' or 'research'.
        # No extra validation needed because KnowledgeMemoryCreate handles it.
        return await self.repository.create_knowledge(
            owner_id=owner_id, 
            workspace_id=workspace_id, 
            data=data
        )
