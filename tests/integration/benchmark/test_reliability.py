import pytest
import uuid
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.repositories.research import ResearchRepository
from app.services.research.lifecycle import ResearchLifecycleService, InvalidTransitionError
from app.models.workspace import Workspace
from app.models.research import ResearchRun

@pytest.mark.asyncio
@pytest.mark.integration
async def test_reliability_transitions():
    async with async_session_maker() as session:
        repo = ResearchRepository(session)
        lifecycle = ResearchLifecycleService(repo)
        
        # Setup
        workspace = Workspace(owner_id=uuid.uuid4())
        session.add(workspace)
        await session.commit()
        
        # Test 1: Worker aborts, gracefully transitions to failed
        run1 = await repo.create_run(workspace.workspace_id, uuid.uuid4(), "Test abort", "legacy")
        # Worker starts
        await lifecycle.transition_run(workspace.workspace_id, run1.run_id, "planning")
        await lifecycle.transition_run(workspace.workspace_id, run1.run_id, "researching")
        
        # Worker crashes or aborts, recovery worker transitions to failed
        run1_failed = await lifecycle.transition_run(workspace.workspace_id, run1.run_id, "failed")
        assert run1_failed.status == "failed"
        
        # Verify terminal state lock
        with pytest.raises(InvalidTransitionError):
            await lifecycle.transition_run(workspace.workspace_id, run1.run_id, "completed")
            
        # Test 2: Budget exhaustion transitions to partial
        run2 = await repo.create_run(workspace.workspace_id, uuid.uuid4(), "Test budget", "legacy")
        await lifecycle.transition_run(workspace.workspace_id, run2.run_id, "planning")
        await lifecycle.transition_run(workspace.workspace_id, run2.run_id, "researching")
        
        # Budget hits max loops
        run2_partial = await lifecycle.transition_run(workspace.workspace_id, run2.run_id, "partial")
        assert run2_partial.status == "partial"
        
        # Verify terminal state lock
        with pytest.raises(InvalidTransitionError):
            await lifecycle.transition_run(workspace.workspace_id, run2.run_id, "researching")

        # Cleanup
        await session.delete(workspace)
        await session.commit()
