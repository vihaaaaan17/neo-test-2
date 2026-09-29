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

    async def delete_workspace(self, workspace_id: UUID, owner_id: UUID) -> tuple[bool, UUID | None]:
        workspace = await self.get_workspace(workspace_id, owner_id)
        if not workspace:
            return False, None
        workspace.status = "archived"
        
        from app.models.open_notebook_binding import OpenNotebookWorkspaceBinding, DeletionTombstone
        result = await self.session.execute(select(OpenNotebookWorkspaceBinding).where(OpenNotebookWorkspaceBinding.workspace_id == workspace_id))
        binding = result.scalars().first()
        tombstone_id = None
        if binding:
            tombstone = DeletionTombstone(
                resource_type="workspace",
                open_notebook_id=binding.open_notebook_notebook_id,
                status="pending"
            )
            self.session.add(tombstone)
            await self.session.flush()
            tombstone_id = tombstone.tombstone_id
            await self.session.delete(binding)
            
        await self.session.commit()
        return True, tombstone_id

    async def create_commit(self, workspace_id: UUID, parent_id: UUID | None, active_knowledge_ids: list[UUID]) -> WorkspaceCommit:
        return await self.create_commit_with_manifest(
            workspace_id=workspace_id,
            parent_id=parent_id,
            active_knowledge_ids=active_knowledge_ids,
            manifest={"knowledge_memory_ids": [str(k_id) for k_id in active_knowledge_ids], "schema_version": 1}
        )

    async def create_commit_with_manifest(
        self,
        workspace_id: UUID,
        parent_id: UUID | None,
        active_knowledge_ids: list[UUID],
        manifest: dict | None = None
    ) -> WorkspaceCommit:
        commit_manifest = manifest or {}
        if "knowledge_memory_ids" not in commit_manifest:
            commit_manifest["knowledge_memory_ids"] = [str(k_id) for k_id in active_knowledge_ids]

        commit = WorkspaceCommit(
            workspace_id=workspace_id,
            parent_id=parent_id,
            active_knowledge_ids=[str(k_id) for k_id in active_knowledge_ids],
            manifest=commit_manifest
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

    async def rollback_workspace_atomic(
        self,
        workspace_id: UUID,
        commit_id: UUID,
        owner_id: UUID
    ) -> tuple[Workspace | None, int]:
        """
        Atomically rolls back the workspace to a target commit under a row lock (FOR UPDATE).
        Increments timeline_epoch atomically to fence out any in-flight workers.
        Returns a tuple of (updated_workspace, new_epoch).
        If workspace or commit is not found / does not belong to workspace, returns (None, 0).
        """
        # 1. Row-lock the workspace
        stmt = (
            select(Workspace)
            .where(
                Workspace.workspace_id == workspace_id,
                Workspace.owner_id == owner_id,
                Workspace.status != "archived"
            )
            .with_for_update()
        )
        result = await self.session.execute(stmt)
        workspace = result.scalars().first()
        if not workspace:
            return None, 0

        # 2. Verify commit exists and belongs to this workspace
        commit = await self.get_commit(commit_id, workspace_id)
        if not commit:
            return None, 0

        # 3. Increment epoch and update active commit pointer atomically
        workspace.timeline_epoch = (workspace.timeline_epoch or 0) + 1
        workspace.active_commit_id = commit_id

        await self.session.commit()
        await self.session.refresh(workspace)
        return workspace, workspace.timeline_epoch

    async def verify_timeline_epoch(self, workspace_id: UUID, expected_epoch: int) -> bool:
        stmt = select(Workspace.timeline_epoch).where(Workspace.workspace_id == workspace_id)
        result = await self.session.execute(stmt)
        current_epoch = result.scalar_one_or_none()
        if current_epoch is None:
            return False
        return current_epoch == expected_epoch
