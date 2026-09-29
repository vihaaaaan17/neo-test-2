from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps.auth import get_current_user
from app.repositories.workspace import WorkspaceRepository
from app.repositories.conversation import ConversationRepository
from app.repositories.scratchpad import ScratchpadRepository
from app.schemas.scratchpad import (
    ScratchpadEntryCreate,
    ScratchpadEntryUpdate,
    ScratchpadEntryResponse,
    ScratchpadEntryListResponse,
)

router = APIRouter()


async def _verify_workspace_access(workspace_id: UUID, user_id: UUID, session: AsyncSession):
    ws_repo = WorkspaceRepository(session)
    ws = await ws_repo.get_workspace(workspace_id, user_id)
    if not ws:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found or access denied"
        )
    return ws


@router.post(
    "/workspaces/{workspace_id}/conversations/{conversation_id}/scratchpad",
    response_model=ScratchpadEntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a scratchpad entry within a conversation"
)
async def create_scratchpad_entry(
    workspace_id: UUID,
    conversation_id: UUID,
    payload: ScratchpadEntryCreate,
    current_user: UUID = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    await _verify_workspace_access(workspace_id, current_user, session)

    conv_repo = ConversationRepository(session)
    conv = await conv_repo.get_conversation(workspace_id, conversation_id)
    if not conv or conv.owner_id != current_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or access denied"
        )

    scratchpad_repo = ScratchpadRepository(session)
    entry = await scratchpad_repo.create_entry(
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        turn_id=payload.turn_id,
        run_id=payload.run_id,
        entry_type=payload.entry_type,
        content=payload.content,
        is_pinned_to_workspace=payload.is_pinned_to_workspace,
        metadata=payload.metadata
    )
    return entry


@router.get(
    "/workspaces/{workspace_id}/conversations/{conversation_id}/scratchpad",
    response_model=ScratchpadEntryListResponse,
    summary="List scratchpad entries for a conversation and workspace pins"
)
async def list_scratchpad_entries(
    workspace_id: UUID,
    conversation_id: UUID,
    lifecycle: Optional[str] = Query("active", description="Filter by lifecycle: active, promoted, dismissed, superseded, or None for all"),
    include_workspace_pinned: bool = Query(True, description="Include active workspace-pinned entries"),
    entry_type: Optional[str] = Query(None, description="Optional filter by entry type"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: UUID = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    await _verify_workspace_access(workspace_id, current_user, session)

    conv_repo = ConversationRepository(session)
    conv = await conv_repo.get_conversation(workspace_id, conversation_id)
    if not conv or conv.owner_id != current_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or access denied"
        )

    scratchpad_repo = ScratchpadRepository(session)
    entries, total = await scratchpad_repo.list_entries(
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        lifecycle=lifecycle if lifecycle != "all" else None,
        include_workspace_pinned=include_workspace_pinned,
        entry_type=entry_type,
        limit=limit,
        offset=offset
    )
    return ScratchpadEntryListResponse(entries=entries, total=total)


@router.get(
    "/workspaces/{workspace_id}/scratchpad/{entry_id}",
    response_model=ScratchpadEntryResponse,
    summary="Get a scratchpad entry"
)
async def get_scratchpad_entry(
    workspace_id: UUID,
    entry_id: UUID,
    current_user: UUID = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    await _verify_workspace_access(workspace_id, current_user, session)

    scratchpad_repo = ScratchpadRepository(session)
    entry = await scratchpad_repo.get_entry(workspace_id, entry_id)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scratchpad entry not found"
        )
    return entry


@router.patch(
    "/workspaces/{workspace_id}/scratchpad/{entry_id}",
    response_model=ScratchpadEntryResponse,
    summary="Update, pin, unpin, or dismiss a scratchpad entry"
)
async def update_scratchpad_entry(
    workspace_id: UUID,
    entry_id: UUID,
    payload: ScratchpadEntryUpdate,
    current_user: UUID = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    await _verify_workspace_access(workspace_id, current_user, session)

    scratchpad_repo = ScratchpadRepository(session)
    entry = await scratchpad_repo.get_entry(workspace_id, entry_id)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scratchpad entry not found"
        )

    if payload.is_pinned_to_workspace is not None:
        if payload.is_pinned_to_workspace:
            await scratchpad_repo.pin_to_workspace(workspace_id, entry_id)
        else:
            await scratchpad_repo.unpin_from_workspace(workspace_id, entry_id)

    if payload.lifecycle is not None:
        await scratchpad_repo.set_lifecycle(workspace_id, entry_id, payload.lifecycle)

    if payload.content is not None or payload.metadata is not None:
        await scratchpad_repo.update_entry(
            workspace_id=workspace_id,
            entry_id=entry_id,
            content=payload.content,
            metadata=payload.metadata
        )

    updated_entry = await scratchpad_repo.get_entry(workspace_id, entry_id)
    return updated_entry
