import pytest
import uuid
import re
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import async_session_maker
from app.models.research import (
    ResearchRun, ResearchTask, ResearchEvidence, ResearchReport, ResearchArtifact
)
from app.models.workspace import Workspace
from app.services.research.provenance import ResearchProvenanceService

async def audit_provenance(session: AsyncSession, run_id: uuid.UUID) -> bool:
    """
    Audits the full provenance chain for a given run_id.
    Chain: Report -> Citations -> Evidence -> Task -> Run -> Workspace
    """
    # 1. Fetch the report
    result = await session.execute(select(ResearchReport).where(ResearchReport.run_id == run_id))
    report = result.scalars().first()
    if not report:
        raise ValueError("Report not found")

    # 2. Extract citations from report content
    # Assuming citations are in the format [evidence_id]
    citations = re.findall(r'\[([a-f0-9\-]{36})\]', report.content)

    if not citations:
        # If no citations, technically valid if it's a short report, but for audit let's assume it should have some.
        return True

    # 3. For each citation, verify the chain
    for citation_str in citations:
        evidence_id = uuid.UUID(citation_str)

        # Verify Evidence exists and is tied to this run
        ev_result = await session.execute(
            select(ResearchEvidence).where(ResearchEvidence.evidence_id == evidence_id, ResearchEvidence.run_id == run_id)
        )
        evidence = ev_result.scalars().first()
        if not evidence:
            raise ValueError(f"Fabricated citation {evidence_id}")

        # Verify Task exists
        if evidence.task_id:
            task_res = await session.execute(
                select(ResearchTask).where(ResearchTask.task_id == evidence.task_id, ResearchTask.run_id == run_id)
            )
            task = task_res.scalars().first()
            if not task:
                raise ValueError(f"Evidence {evidence_id} linked to invalid task {evidence.task_id}")

    return True

@pytest.mark.asyncio
async def test_provenance_audit_success():
    async with async_session_maker() as session:
        # Setup
        workspace = Workspace(owner_id=uuid.uuid4())
        session.add(workspace)
        await session.commit()

        run = ResearchRun(workspace_id=workspace.workspace_id, owner_id=uuid.uuid4(), objective="Test", engine="test")
        session.add(run)
        await session.commit()

        task = ResearchTask(run_id=run.run_id, objective="Test Task")
        session.add(task)
        await session.commit()

        evidence = ResearchEvidence(run_id=run.run_id, task_id=task.task_id, content="Test content")
        session.add(evidence)
        await session.commit()

        report = ResearchReport(run_id=run.run_id, objective="Test", content=f"This is a report with a citation [{evidence.evidence_id}].")
        session.add(report)
        await session.commit()

        # Audit
        is_valid = await audit_provenance(session, run.run_id)
        assert is_valid is True

@pytest.mark.asyncio
async def test_provenance_audit_failure_fabricated_citation():
    async with async_session_maker() as session:
        # Setup
        workspace = Workspace(owner_id=uuid.uuid4())
        session.add(workspace)
        await session.commit()

        run = ResearchRun(workspace_id=workspace.workspace_id, owner_id=uuid.uuid4(), objective="Test", engine="test")
        session.add(run)
        await session.commit()

        report = ResearchReport(run_id=run.run_id, objective="Test", content=f"This is a report with a hallucinated citation [{uuid.uuid4()}].")
        session.add(report)
        await session.commit()

        # Audit should fail
        with pytest.raises(ValueError, match="Fabricated citation"):
            await audit_provenance(session, run.run_id)

@pytest.mark.asyncio
async def test_claim_citation_mapping_success():
    async with async_session_maker() as session:
        workspace = Workspace(owner_id=uuid.uuid4())
        session.add(workspace)
        await session.commit()

        run = ResearchRun(workspace_id=workspace.workspace_id, owner_id=uuid.uuid4(), objective="Test", engine="test")
        session.add(run)
        await session.commit()

        evidence = ResearchEvidence(run_id=run.run_id, content="Evidence content")
        session.add(evidence)
        await session.commit()

        report = ResearchReport(
            run_id=run.run_id,
            objective="Test",
            content="Report",
            citations={
                "claim_1": [str(evidence.evidence_id)]
            },
            provenance_version="v1",
            status="verified"
        )
        session.add(report)
        await session.commit()

        service = ResearchProvenanceService(session)
        is_valid = await service.audit_claim_citations(workspace.workspace_id, run.run_id, report.report_id)
        assert is_valid is True

@pytest.mark.asyncio
async def test_claim_citation_mapping_cross_run_failure():
    async with async_session_maker() as session:
        workspace = Workspace(owner_id=uuid.uuid4())
        session.add(workspace)
        await session.commit()

        run1 = ResearchRun(workspace_id=workspace.workspace_id, owner_id=uuid.uuid4(), objective="Run 1", engine="test")
        run2 = ResearchRun(workspace_id=workspace.workspace_id, owner_id=uuid.uuid4(), objective="Run 2", engine="test")
        session.add(run1)
        session.add(run2)
        await session.commit()

        evidence_run1 = ResearchEvidence(run_id=run1.run_id, content="Evidence from Run 1")
        session.add(evidence_run1)
        await session.commit()

        # Report in Run 2 trying to cite evidence from Run 1
        report = ResearchReport(
            run_id=run2.run_id,
            objective="Test",
            content="Report",
            citations={
                "claim_1": [str(evidence_run1.evidence_id)]
            }
        )
        session.add(report)
        await session.commit()

        service = ResearchProvenanceService(session)
        with pytest.raises(ValueError, match="Fabricated citation"):
            await service.audit_claim_citations(workspace.workspace_id, run2.run_id, report.report_id)
