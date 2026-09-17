from uuid import UUID
from typing import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.knowledge import KnowledgeMemory
from app.schemas.knowledge import KnowledgeMemoryCreate

class KnowledgeRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_knowledge(self, owner_id: UUID, workspace_id: UUID, data: KnowledgeMemoryCreate) -> KnowledgeMemory:
        db_knowledge = KnowledgeMemory(
            owner_id=owner_id,
            workspace_id=workspace_id,
            knowledge_type=data.knowledge_type,
            content=data.content,
            status=data.status,
            provenance=data.provenance.model_dump(),
            confidence=data.confidence,
            tags=data.tags,
            entities=data.entities,
            domain=data.domain,
            version=data.version
        )
        self.session.add(db_knowledge)
        await self.session.commit()
        await self.session.refresh(db_knowledge)
        return db_knowledge

    async def get_knowledge(self, knowledge_id: UUID, owner_id: UUID) -> KnowledgeMemory | None:
        result = await self.session.execute(
            select(KnowledgeMemory)
            .where(KnowledgeMemory.knowledge_id == knowledge_id)
            .where(KnowledgeMemory.owner_id == owner_id)
        )
        return result.scalars().first()

    async def list_workspace_knowledge(self, workspace_id: UUID, owner_id: UUID) -> Sequence[KnowledgeMemory]:
        result = await self.session.execute(
            select(KnowledgeMemory)
            .where(KnowledgeMemory.workspace_id == workspace_id)
            .where(KnowledgeMemory.owner_id == owner_id)
            .order_by(KnowledgeMemory.created_at.desc())
        )
        return result.scalars().all()
