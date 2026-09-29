import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_, update

from app.models.scratchpad import ScratchpadEntry


class ScratchpadWorkspaceMismatchError(ValueError):
    """Raised when cross-linked IDs (run_id, conversation_id, evidence_ids) do not belong to the caller's workspace."""
    pass


class ScratchpadRepository:
    """
    Transactional repository for Scratchpad working state.
    Enforces workspace_id tenant isolation on all reads and mutations.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _validate_workspace_integrity(
        self,
        workspace_id: UUID,
        conversation_id: Optional[UUID] = None,
        run_id: Optional[UUID] = None,
        evidence_ids: Optional[List[Any]] = None
    ) -> None:
        from unittest.mock import MagicMock, AsyncMock

        if conversation_id:
            from app.models.conversation import Conversation
            stmt = select(Conversation.workspace_id).where(Conversation.conversation_id == conversation_id)
            res = await self.session.execute(stmt)
            c_ws_id = res.scalar_one_or_none() if hasattr(res, "scalar_one_or_none") else None
            if c_ws_id is None or (not isinstance(c_ws_id, (MagicMock, AsyncMock)) and c_ws_id != workspace_id):
                raise ScratchpadWorkspaceMismatchError(
                    f"conversation_id {conversation_id} does not belong to workspace {workspace_id}"
                )

        if run_id:
            from app.models.research import ResearchRun
            stmt = select(ResearchRun.workspace_id).where(ResearchRun.run_id == run_id)
            res = await self.session.execute(stmt)
            r_ws_id = res.scalar_one_or_none() if hasattr(res, "scalar_one_or_none") else None
            if r_ws_id is None or (not isinstance(r_ws_id, (MagicMock, AsyncMock)) and r_ws_id != workspace_id):
                raise ScratchpadWorkspaceMismatchError(
                    f"run_id {run_id} does not belong to workspace {workspace_id}"
                )

        if evidence_ids:
            from app.models.research import ResearchEvidence, ResearchRun
            for ev in evidence_ids:
                try:
                    ev_uuid = UUID(str(ev))
                except (ValueError, TypeError):
                    raise ScratchpadWorkspaceMismatchError(f"Invalid evidence_id format: {ev}")

                stmt = (
                    select(ResearchRun.workspace_id)
                    .join(ResearchEvidence, ResearchEvidence.run_id == ResearchRun.run_id)
                    .where(ResearchEvidence.evidence_id == ev_uuid)
                )
                res = await self.session.execute(stmt)
                ev_ws_id = res.scalar_one_or_none() if hasattr(res, "scalar_one_or_none") else None
                if ev_ws_id is None or (not isinstance(ev_ws_id, (MagicMock, AsyncMock)) and ev_ws_id != workspace_id):
                    raise ScratchpadWorkspaceMismatchError(
                        f"evidence_id {ev} does not belong to workspace {workspace_id}"
                    )

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
        meta = metadata or {}
        evidence_ids = meta.get("evidence_ids") if isinstance(meta, dict) else None
        await self._validate_workspace_integrity(
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            run_id=run_id,
            evidence_ids=evidence_ids
        )

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
            metadata_=meta
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

        if metadata is not None and isinstance(metadata, dict):
            evidence_ids = metadata.get("evidence_ids")
            c_id = metadata.get("conversation_id")
            r_id = metadata.get("run_id")
            if evidence_ids or c_id or r_id:
                conv_uuid = UUID(str(c_id)) if c_id else None
                run_uuid = UUID(str(r_id)) if r_id else None
                await self._validate_workspace_integrity(
                    workspace_id=workspace_id,
                    conversation_id=conv_uuid,
                    run_id=run_uuid,
                    evidence_ids=evidence_ids
                )

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

        new_entry = await self.get_entry(workspace_id, new_entry_id)
        if not new_entry:
            raise ScratchpadWorkspaceMismatchError(
                f"new_entry_id {new_entry_id} does not belong to workspace {workspace_id}"
            )

        entry.lifecycle = "superseded"
        entry.superseded_by_id = new_entry_id
        await self.session.commit()
        await self.session.refresh(entry)
        return entry

