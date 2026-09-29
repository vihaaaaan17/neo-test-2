import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_, update

from app.models.scratchpad import ScratchpadEntry


class ScratchpadRepository:
    """
    Transactional repository for Scratchpad working state.
    Enforces workspace_id tenant isolation on all reads and mutations.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_entry(
        self,
        workspace_id: UUID,
        entry_type: str,
        content: str,
        conversation_id: Optional[UUID] = None,
        turn_id: Optional[UUID] = None,
        run_id: Optional[UUID] = None,
        is_pinned_to_workspace: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ScratchpadEntry:
        pinned_at = datetime.now(timezone.utc) if is_pinned_to_workspace else None
        entry = ScratchpadEntry(
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            turn_id=turn_id,
            run_id=run_id,
            entry_type=entry_type,
            lifecycle="active",
            content=content,
            is_pinned_to_workspace=is_pinned_to_workspace,
            pinned_at=pinned_at,
            metadata_=metadata or {}
        )
        self.session.add(entry)
        await self.session.commit()
        await self.session.refresh(entry)
        return entry

    async def get_entry(self, workspace_id: UUID, entry_id: UUID) -> Optional[ScratchpadEntry]:
        stmt = select(ScratchpadEntry).where(
            ScratchpadEntry.entry_id == entry_id,
            ScratchpadEntry.workspace_id == workspace_id
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_entries(
        self,
        workspace_id: UUID,
        conversation_id: Optional[UUID] = None,
        lifecycle: Optional[str] = "active",
        include_workspace_pinned: bool = True,
        entry_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[ScratchpadEntry], int]:
        """
        Lists scratchpad entries with tenant isolation.
        If conversation_id is supplied and include_workspace_pinned is True,
        returns entries belonging to this conversation PLUS any active workspace-pinned entries.
        """
        conditions = [ScratchpadEntry.workspace_id == workspace_id]

        if lifecycle:
            conditions.append(ScratchpadEntry.lifecycle == lifecycle)

        if entry_type:
            conditions.append(ScratchpadEntry.entry_type == entry_type)

        if conversation_id:
            if include_workspace_pinned:
                conditions.append(
                    or_(
                        ScratchpadEntry.conversation_id == conversation_id,
                        ScratchpadEntry.is_pinned_to_workspace == True
                    )
                )
            else:
                conditions.append(ScratchpadEntry.conversation_id == conversation_id)

        # Count total
        count_stmt = select(func.count(ScratchpadEntry.entry_id)).where(*conditions)
        total_res = await self.session.execute(count_stmt)
        total = total_res.scalar_one()

        # Query items
        stmt = select(ScratchpadEntry).where(*conditions).order_by(
            ScratchpadEntry.is_pinned_to_workspace.desc(),
            ScratchpadEntry.created_at.desc()
        ).limit(limit).offset(offset)

        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def update_entry(
        self,
        workspace_id: UUID,
        entry_id: UUID,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[ScratchpadEntry]:
        entry = await self.get_entry(workspace_id, entry_id)
        if not entry:
            return None

        if content is not None:
            entry.content = content
        if metadata is not None:
            entry.metadata_ = metadata

        await self.session.commit()
        await self.session.refresh(entry)
        return entry

    async def set_lifecycle(
        self,
        workspace_id: UUID,
        entry_id: UUID,
        lifecycle: str
    ) -> Optional[ScratchpadEntry]:
        entry = await self.get_entry(workspace_id, entry_id)
        if not entry:
            return None

        entry.lifecycle = lifecycle
        await self.session.commit()
        await self.session.refresh(entry)
        return entry

    async def pin_to_workspace(self, workspace_id: UUID, entry_id: UUID) -> Optional[ScratchpadEntry]:
        entry = await self.get_entry(workspace_id, entry_id)
        if not entry:
            return None

        entry.is_pinned_to_workspace = True
        entry.pinned_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(entry)
        return entry

    async def unpin_from_workspace(self, workspace_id: UUID, entry_id: UUID) -> Optional[ScratchpadEntry]:
        entry = await self.get_entry(workspace_id, entry_id)
        if not entry:
            return None

        entry.is_pinned_to_workspace = False
        entry.pinned_at = None
        await self.session.commit()
        await self.session.refresh(entry)
        return entry

    async def supersede_entry(
        self,
        workspace_id: UUID,
        old_entry_id: UUID,
        new_entry_id: UUID
    ) -> Optional[ScratchpadEntry]:
        entry = await self.get_entry(workspace_id, old_entry_id)
        if not entry:
            return None

        entry.lifecycle = "superseded"
        entry.superseded_by_id = new_entry_id
        await self.session.commit()
        await self.session.refresh(entry)
        return entry
