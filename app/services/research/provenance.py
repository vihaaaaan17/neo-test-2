import uuid
from typing import Optional, Tuple, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.source import Source, SourceSnapshot

class ResearchProvenanceService:
    """
    Manages the mapping of external citations/evidence to canonical workspace Sources.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def resolve_source(self, workspace_id: uuid.UUID, citation: Dict[str, Any]) -> Tuple[Optional[uuid.UUID], Optional[Dict[str, Any]]]:
        """
        Attempts to resolve an external citation to an existing workspace Source.
        Returns a tuple: (resolved_source_id, raw_provenance_if_unresolved)
        
        If resolved successfully, the second element can be None.
        If unresolved, the first element is None, and the second is the raw citation dict.
        """
        url = citation.get("url")
        if not url:
            # Without a URL or identifier, we cannot resolve to a specific source
            return None, citation
            
        # Attempt to find a source snapshot with a matching file_uri in this workspace
        stmt = (
            select(Source.source_id)
            .join(SourceSnapshot)
            .where(Source.workspace_id == workspace_id)
            .where(SourceSnapshot.file_uri == url)
        )
        
        result = await self.session.execute(stmt)
        source_id = result.scalar_one_or_none()
        
        if source_id:
            # Found canonical source
            return source_id, None
            
        # Unresolved
        return None, citation
