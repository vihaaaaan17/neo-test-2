from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.workspace import Workspace
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
