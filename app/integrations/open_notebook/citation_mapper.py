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
        logger.warning(f"Partial provenance: some upstream IDs could not be mapped to workspace {workspace_id}: {unmapped}")
    
    return list(valid_source_ids), partial
