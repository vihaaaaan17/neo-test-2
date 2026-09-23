import uuid
from typing import Optional, Tuple, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.source import Source, SourceSnapshot
from app.models.research import ResearchRun, ResearchEvidence, ResearchReport

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

    async def audit_claim_citations(self, workspace_id: uuid.UUID, run_id: uuid.UUID, report_id: uuid.UUID) -> bool:
        """
        Audits the full provenance chain for a given report_id.
        Chain: Report -> Citations -> Evidence -> Run -> Workspace

        Returns True if all citations are valid, raises ValueError if any are invalid.
        """
        # 1. Fetch the report
        result = await self.session.execute(
            select(ResearchReport).where(
                ResearchReport.report_id == report_id,
                ResearchReport.run_id == run_id
            )
        )
        report = result.scalars().first()
        if not report:
            raise ValueError("Report not found")

        # 2. Verify workspace boundary
        run_result = await self.session.execute(
            select(ResearchRun).where(
                ResearchRun.run_id == run_id,
                ResearchRun.workspace_id == workspace_id
            )
        )
        run = run_result.scalars().first()
        if not run:
            raise ValueError("Run not found in workspace")

        # 3. Extract citations from report
        citations = report.citations or {}
        if isinstance(citations, dict):
            evidence_id_list = []
            for claim_id, val in citations.items():
                if isinstance(val, list):
                    evidence_id_list.extend(val)
                elif isinstance(val, (str, uuid.UUID)):
                    evidence_id_list.append(val)
        elif isinstance(citations, list):
            evidence_id_list = citations
        else:
            evidence_id_list = []

        # 4. For each citation, verify the chain
        for ev_id in evidence_id_list:
            ev_uuid = uuid.UUID(str(ev_id))
            ev_result = await self.session.execute(
                select(ResearchEvidence).where(
                    ResearchEvidence.evidence_id == ev_uuid,
                    ResearchEvidence.run_id == run_id
                )
            )
            evidence = ev_result.scalars().first()
            if not evidence:
                raise ValueError(f"Fabricated citation {ev_uuid}")

        return True
