import logging
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.open_notebook_binding import OpenNotebookSourceBinding
from app.models.source import Source

logger = logging.getLogger(__name__)

async def map_citations(
    upstream_ids: list[str],
    workspace_id: UUID,
    db: AsyncSession
) -> tuple[list[UUID], bool]:
    """
    Map upstream Open Notebook source IDs back to canonical Neosis source_ids.
    Ensures that mapped sources actually belong to the given workspace_id.
    
    Returns:
        tuple containing:
        - List of mapped canonical Neosis source_ids (UUIDs)
        - Boolean indicating if provenance is partial (i.e. some upstream IDs could not be mapped)
    """
    if not upstream_ids:
        return [], False

    stmt = select(OpenNotebookSourceBinding).where(
        OpenNotebookSourceBinding.open_notebook_source_id.in_(upstream_ids)
    )
    result = await db.execute(stmt)
    bindings = result.scalars().all()
    
    source_ids = [b.source_id for b in bindings]
    
    if not source_ids:
        logger.warning(f"Could not map any Open Notebook IDs to Neosis source IDs: {upstream_ids}")
        return [], len(upstream_ids) > 0
        
    stmt = select(Source.source_id).where(
        Source.source_id.in_(source_ids),
        Source.workspace_id == workspace_id
    )
    result = await db.execute(stmt)
    valid_source_ids = result.scalars().all()
    
    partial = len(valid_source_ids) < len(upstream_ids)
    if partial:
        unmapped = set(upstream_ids) - {b.open_notebook_source_id for b in bindings if b.source_id in valid_source_ids}
    return list(valid_source_ids), partial


async def map_canonical_sources_to_upstream(
    canonical_source_ids: list[UUID],
    workspace_id: UUID,
    db: AsyncSession
) -> list[str]:
    """
    Map canonical Neosis source_ids (UUIDs) to upstream Open Notebook source IDs (strings).
    Ensures that mapped sources actually belong to the given workspace_id.
    """
    if not canonical_source_ids:
        return []

    canonical_set = {UUID(str(s)) for s in canonical_source_ids}
    stmt = (
        select(OpenNotebookSourceBinding.open_notebook_source_id)
        .join(Source, Source.source_id == OpenNotebookSourceBinding.source_id)
        .where(
            Source.workspace_id == workspace_id,
            OpenNotebookSourceBinding.source_id.in_(canonical_set),
            OpenNotebookSourceBinding.open_notebook_source_id.isnot(None)
        )
    )
    result = await db.execute(stmt)
    return [str(s) for s in result.scalars().all() if s]

async def list_workspace_upstream_source_ids(
    workspace_id: UUID,
    db: AsyncSession
) -> list[str]:
    """All projected Open Notebook source IDs belonging to a workspace (used when no explicit scope is given)."""
    stmt = (
        select(OpenNotebookSourceBinding.open_notebook_source_id)
        .join(Source, Source.source_id == OpenNotebookSourceBinding.source_id)
        .where(
            Source.workspace_id == workspace_id,
            OpenNotebookSourceBinding.open_notebook_source_id.isnot(None)
        )
    )
    result = await db.execute(stmt)
    return sorted({str(s) for s in result.scalars().all() if s})

