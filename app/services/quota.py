from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from fastapi import HTTPException, status
from uuid import UUID

from app.core.config import settings
from app.models.workspace import Workspace
from app.models.source import Source, SourceSnapshot
from app.models.knowledge import KnowledgeMemory

class QuotaService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_workspace_limit(self, owner_id: UUID) -> None:
        """Check if user has exceeded their workspace limit."""
        result = await self.db.execute(
            select(func.count(Workspace.workspace_id)).where(Workspace.owner_id == owner_id)
        )
        count = result.scalar() or 0
        if count >= settings.MAX_WORKSPACES_PER_USER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Quota exceeded: Maximum {settings.MAX_WORKSPACES_PER_USER} workspaces per user."
            )

    async def check_source_limit(self, workspace_id: UUID) -> None:
        """Check if workspace has exceeded its source count limit."""
        result = await self.db.execute(
            select(func.count(Source.source_id)).where(Source.workspace_id == workspace_id)
        )
        count = result.scalar() or 0
        if count >= settings.MAX_SOURCES_PER_WORKSPACE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Quota exceeded: Maximum {settings.MAX_SOURCES_PER_WORKSPACE} sources per workspace."
            )

    async def check_storage_limit(self, workspace_id: UUID, new_bytes: int) -> None:
        """Check if workspace has exceeded its total storage limit."""
        result = await self.db.execute(
            select(func.sum(SourceSnapshot.size))
            .join(Source)
            .where(Source.workspace_id == workspace_id)
        )
        total_storage = result.scalar() or 0
        if total_storage + new_bytes > settings.MAX_STORAGE_BYTES_PER_WORKSPACE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Quota exceeded: Workspace storage limit reached ({settings.MAX_STORAGE_BYTES_PER_WORKSPACE / 1_000_000:.1f} MB)."
            )

    async def check_knowledge_limit(self, workspace_id: UUID) -> None:
        """Check if workspace has exceeded its knowledge memory limit."""
        result = await self.db.execute(
            select(func.count(KnowledgeMemory.knowledge_id)).where(KnowledgeMemory.workspace_id == workspace_id)
        )
        count = result.scalar() or 0
        if count >= settings.MAX_KNOWLEDGE_PER_WORKSPACE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Quota exceeded: Maximum {settings.MAX_KNOWLEDGE_PER_WORKSPACE} knowledge nodes per workspace."
            )

def get_quota_service(db: AsyncSession) -> QuotaService:
    return QuotaService(db)
