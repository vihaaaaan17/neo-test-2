from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.episodic import EpisodicMemory
from app.schemas.episodic import EpisodicMemoryCreate

class EpisodicRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_episode(self, owner_id: UUID, workspace_id: UUID, data: EpisodicMemoryCreate) -> EpisodicMemory:
        db_episode = EpisodicMemory(
            owner_id=owner_id,
            workspace_id=workspace_id,
            event_type=data.event_type,
            summary=data.summary,
            importance=data.importance,
            run_id=data.run_id,
            task_id=data.task_id,
            outcome=data.outcome,
            entities=data.entities,
            embedding_ref=data.embedding_ref
        )
        self.session.add(db_episode)
        await self.session.commit()
        await self.session.refresh(db_episode)
        return db_episode

    async def get_episode_by_run_id(
        self, workspace_id: UUID, run_id: UUID
    ) -> EpisodicMemory | None:
        """Used by the background worker to detect duplicate compress_episodic_job calls."""
        result = await self.session.execute(
            select(EpisodicMemory).where(
                EpisodicMemory.workspace_id == workspace_id,
                EpisodicMemory.run_id == run_id,
            )
        )
        return result.scalars().first()
