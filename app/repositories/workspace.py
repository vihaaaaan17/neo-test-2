from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.workspace import Workspace, WorkspaceCommit
from app.schemas.workspace import WorkspaceCreate, WorkspaceUpdate

class WorkspaceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_workspace(self, owner_id: UUID) -> Workspace:
        workspace = Workspace(owner_id=owner_id)
        self.session.add(workspace)
        await self.session.commit()
        await self.session.refresh(workspace)
        return workspace

    async def get_workspace(self, workspace_id: UUID, owner_id: UUID) -> Workspace | None:
        result = await self.session.execute(
            select(Workspace).where(
                Workspace.workspace_id == workspace_id, 
                Workspace.owner_id == owner_id,
                Workspace.status != "archived"
            )
        )
        return result.scalars().first()

    async def update_workspace(self, workspace_id: UUID, owner_id: UUID, update_data: WorkspaceUpdate) -> Workspace | None:
        workspace = await self.get_workspace(workspace_id, owner_id)
        if not workspace:
            return None
        workspace.status = update_data.status
        await self.session.commit()
        await self.session.refresh(workspace)
        return workspace

    async def delete_workspace(self, workspace_id: UUID, owner_id: UUID) -> bool:
        workspace = await self.get_workspace(workspace_id, owner_id)
        if not workspace:
            return False
        workspace.status = "archived"
        await self.session.commit()
        return True

    async def create_commit(self, workspace_id: UUID, parent_id: UUID | None, active_knowledge_ids: list[UUID]) -> WorkspaceCommit:
        commit = WorkspaceCommit(
            workspace_id=workspace_id,
            parent_id=parent_id,
            active_knowledge_ids=[str(k_id) for k_id in active_knowledge_ids]
        )
        self.session.add(commit)
        await self.session.commit()
        await self.session.refresh(commit)
        return commit

    async def get_commit(self, commit_id: UUID, workspace_id: UUID) -> WorkspaceCommit | None:
        result = await self.session.execute(
            select(WorkspaceCommit).where(
                WorkspaceCommit.commit_id == commit_id,
                WorkspaceCommit.workspace_id == workspace_id
            )
        )
        return result.scalars().first()

    async def set_active_commit(self, workspace_id: UUID, commit_id: UUID) -> Workspace | None:
        result = await self.session.execute(
            select(Workspace).where(
                Workspace.workspace_id == workspace_id
            )
        )
        workspace = result.scalars().first()
        if not workspace:
            return None
        workspace.active_commit_id = commit_id
        await self.session.commit()
        await self.session.refresh(workspace)
        return workspace
