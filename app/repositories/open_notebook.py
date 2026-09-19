from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
import logging

from app.models.open_notebook_binding import OpenNotebookWorkspaceBinding, OpenNotebookSourceBinding

logger = logging.getLogger(__name__)

class OpenNotebookRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_workspace_binding(self, workspace_id: UUID) -> Optional[OpenNotebookWorkspaceBinding]:
        result = await self.session.execute(
            select(OpenNotebookWorkspaceBinding).where(OpenNotebookWorkspaceBinding.workspace_id == workspace_id)
        )
        return result.scalars().first()
        
    async def get_notebook_id_for_workspace(self, workspace_id: UUID) -> Optional[str]:
        binding = await self.get_workspace_binding(workspace_id)
        return binding.open_notebook_notebook_id if binding else None

    async def create_workspace_binding(self, workspace_id: UUID, notebook_id: str) -> OpenNotebookWorkspaceBinding:
        existing = await self.get_workspace_binding(workspace_id)
        if existing:
            return existing
            
        binding = OpenNotebookWorkspaceBinding(
            workspace_id=workspace_id,
            open_notebook_notebook_id=notebook_id
        )
        self.session.add(binding)
        try:
            await self.session.commit()
            await self.session.refresh(binding)
            return binding
        except IntegrityError:
            await self.session.rollback()
            return await self.get_workspace_binding(workspace_id)
            
    async def delete_workspace_binding(self, workspace_id: UUID) -> bool:
        binding = await self.get_workspace_binding(workspace_id)
        if binding:
            await self.session.delete(binding)
            await self.session.commit()
            return True
        return False

    async def get_source_binding(self, source_id: UUID, snapshot_id: UUID) -> Optional[OpenNotebookSourceBinding]:
        result = await self.session.execute(
            select(OpenNotebookSourceBinding).where(
                OpenNotebookSourceBinding.source_id == source_id,
                OpenNotebookSourceBinding.snapshot_id == snapshot_id
            )
        )
        return result.scalars().first()

    async def claim_projection_job(self, source_id: UUID, snapshot_id: UUID, checksum: str) -> Optional[OpenNotebookSourceBinding]:
        """
        Atomically claims a projection job for a given source and snapshot.
        Creates a new binding in PENDING/PROJECTING state.
        Returns the created binding, or None if it already exists/is claimed.
        """
        binding = OpenNotebookSourceBinding(
            source_id=source_id,
            snapshot_id=snapshot_id,
            checksum_sha256=checksum,
            projection_status="PROJECTING"
        )
        self.session.add(binding)
        try:
            await self.session.commit()
            await self.session.refresh(binding)
            return binding
        except IntegrityError:
            await self.session.rollback()
            # Already exists, cannot claim
            return None
            
    async def update_projection_status(
        self, 
        source_id: UUID, 
        snapshot_id: UUID, 
        status: str,
        open_notebook_source_id: Optional[str] = None,
        error_meta: Optional[Dict[str, Any]] = None
    ) -> Optional[OpenNotebookSourceBinding]:
        binding = await self.get_source_binding(source_id, snapshot_id)
        if not binding:
            return None
            
        binding.projection_status = status # type: ignore
        
        if open_notebook_source_id:
            binding.open_notebook_source_id = open_notebook_source_id # type: ignore
            
        if status == "ACTIVE":
            binding.projected_at = datetime.now(timezone.utc) # type: ignore
            
        if error_meta:
            binding.error_meta = error_meta # type: ignore
            
        await self.session.commit()
        await self.session.refresh(binding)
        return binding

    async def get_active_projections_for_source(self, source_id: UUID) -> List[OpenNotebookSourceBinding]:
        """Returns all bindings for a source_id that are successfully projected to ON"""
        result = await self.session.execute(
            select(OpenNotebookSourceBinding).where(
                OpenNotebookSourceBinding.source_id == source_id,
                OpenNotebookSourceBinding.projection_status == "ACTIVE"
            )
        )
        return list(result.scalars().all())

    async def create_tombstone_and_delete_source_binding(self, source_id: UUID, snapshot_id: UUID):
        binding = await self.get_source_binding(source_id, snapshot_id)
        if binding:
            from app.models.open_notebook_binding import DeletionTombstone
            tombstone = DeletionTombstone(
                resource_type="source",
                open_notebook_id=binding.open_notebook_source_id,
                status="pending"
            )
            self.session.add(tombstone)
            await self.session.flush()
            
            await self.session.delete(binding)
            await self.session.commit()
            return tombstone
        return None
