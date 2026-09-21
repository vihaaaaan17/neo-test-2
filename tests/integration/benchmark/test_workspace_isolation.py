import pytest
import uuid
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_session_maker
from app.repositories.research import ResearchRepository
from app.models.workspace import Workspace
from app.models.research import ResearchRun

@pytest.mark.asyncio
@pytest.mark.integration
async def test_workspace_isolation():
    async with async_session_maker() as session:
        repo = ResearchRepository(session)
        
        ws_a = Workspace(owner_id=uuid.uuid4())
        ws_b = Workspace(owner_id=uuid.uuid4())
        session.add_all([ws_a, ws_b])
        await session.commit()
        
        owner_id = uuid.uuid4()
        
        # Create a run in Workspace A
        run_a = await repo.create_run(ws_a.workspace_id, owner_id, "WS A Objective", "test_engine")
        
        # Create a run in Workspace B
        run_b = await repo.create_run(ws_b.workspace_id, owner_id, "WS B Objective", "test_engine")
        
        # Add evidence to Run A
        ev_a = await repo.create_evidence(ws_a.workspace_id, run_a.run_id, content="Evidence for A")
        
        # Add report to Run A
        rep_a = await repo.create_report(ws_a.workspace_id, run_a.run_id, "Obj A", "Report A")
        
        # Add artifact to Run A
        art_a = await repo.create_artifact(ws_a.workspace_id, run_a.run_id, "test_artifact", {"data": "test"})
        
        # 1. Attempt to get Run A from Workspace B
        run_a_fetched = await repo.get_run(ws_b.workspace_id, run_a.run_id)
        assert run_a_fetched is None, "Should not return run from different workspace"
        
        # 2. Attempt to create evidence for Run A using Workspace B's ID
        with pytest.raises(Exception):
            await repo.create_evidence(ws_b.workspace_id, run_a.run_id, content="Rogue evidence")
            
        # 3. Attempt to get Evidence A from Workspace B
        with pytest.raises(Exception):
            await repo.get_evidence(ws_b.workspace_id, run_a.run_id, ev_a.evidence_id)
        
        # 4. Attempt to list evidence for Run A using Workspace B
        with pytest.raises(Exception):
            await repo.list_evidence_for_run(ws_b.workspace_id, run_a.run_id)
            
        # 5. Attempt to get Report A from Workspace B
        with pytest.raises(Exception):
            await repo.get_report(ws_b.workspace_id, run_a.run_id, rep_a.report_id)
        
        # 6. Attempt to get Artifact A from Workspace B
        with pytest.raises(Exception):
            await repo.get_artifact(ws_b.workspace_id, run_a.run_id, art_a.artifact_id)
        
        # Clean up is handled by testing DB teardown or rolling back if needed, but since it's an integration DB, we can just leave it or delete.
        await session.delete(ws_a)
        await session.delete(ws_b)
        await session.commit()
