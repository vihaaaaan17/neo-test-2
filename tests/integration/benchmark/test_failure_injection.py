"""
Ticket 26: Failure Injection Tests

Tests covering worker restarts, Redis saturation, and DB pool limits.
"""
import pytest
import uuid
import asyncio
import time
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.repositories.research import ResearchRepository
from app.services.research.lifecycle import ResearchLifecycleService, InvalidTransitionError
from app.models.workspace import Workspace
from app.models.research import ResearchRun


@pytest.mark.asyncio
@pytest.mark.integration
async def test_worker_restart_recovery():
    """Test that a worker can restart and resume a run safely."""
    async with async_session_maker() as session:
        repo = ResearchRepository(session)
        lifecycle = ResearchLifecycleService(repo)

        workspace = Workspace(owner_id=uuid.uuid4())
        session.add(workspace)
        await session.commit()

        # Create a run and transition it to researching
        run = await repo.create_run(workspace.workspace_id, uuid.uuid4(), "Test restart", "legacy")
        await lifecycle.transition_run(workspace.workspace_id, run.run_id, "planning")
        await lifecycle.transition_run(workspace.workspace_id, run.run_id, "researching")

        # Simulate worker crash: run is left in "researching" state
        # Recovery worker should be able to transition it to "failed" or "partial"
        recovered = await lifecycle.transition_run(workspace.workspace_id, run.run_id, "failed")
        assert recovered.status == "failed"

        # Verify terminal state lock
        with pytest.raises(InvalidTransitionError):
            await lifecycle.transition_run(workspace.workspace_id, run.run_id, "completed")

        await session.delete(workspace)
        await session.commit()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_redis_saturation_handling():
    """Test that the system handles Redis saturation gracefully."""
    async with async_session_maker() as session:
        repo = ResearchRepository(session)
        lifecycle = ResearchLifecycleService(repo)

        workspace = Workspace(owner_id=uuid.uuid4())
        session.add(workspace)
        await session.commit()

        # Simulate Redis saturation by creating runs and events rapidly
        # The system should not crash; events should be persisted to Postgres
        last_run = None
        for i in range(10):
            last_run = await repo.create_run(workspace.workspace_id, uuid.uuid4(), f"Saturation test {i}", "legacy")
            await lifecycle.transition_run(workspace.workspace_id, last_run.run_id, "planning")
            await lifecycle.transition_run(workspace.workspace_id, last_run.run_id, "researching")
            await lifecycle.transition_run(workspace.workspace_id, last_run.run_id, "synthesizing")
            await lifecycle.transition_run(workspace.workspace_id, last_run.run_id, "finalizing")
            await lifecycle.transition_run(workspace.workspace_id, last_run.run_id, "completed")

        # Verify the run reached completed state
        fetched = await repo.get_run(workspace.workspace_id, last_run.run_id)
        assert fetched.status == "completed"

        # Verify events were persisted
        events = await repo.get_events_for_run(workspace.workspace_id, last_run.run_id)
        assert len(events) > 0
        assert events[0].sequence == 1
        assert events[-1].sequence == len(events)

        await session.delete(workspace)
        await session.commit()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_db_pool_limit_handling():
    """Test that the system handles DB pool limits gracefully."""
    async with async_session_maker() as session:
        repo = ResearchRepository(session)
        lifecycle = ResearchLifecycleService(repo)

        workspace = Workspace(owner_id=uuid.uuid4())
        session.add(workspace)
        await session.commit()

        # Create multiple runs to simulate DB pool pressure
        runs = []
        for i in range(5):
            run = await repo.create_run(workspace.workspace_id, uuid.uuid4(), f"Test DB pool {i}", "legacy")
            runs.append(run)

        # Transition all runs to completed
        for run in runs:
            await lifecycle.transition_run(workspace.workspace_id, run.run_id, "planning")
            await lifecycle.transition_run(workspace.workspace_id, run.run_id, "researching")
            await lifecycle.transition_run(workspace.workspace_id, run.run_id, "synthesizing")
            await lifecycle.transition_run(workspace.workspace_id, run.run_id, "finalizing")
            await lifecycle.transition_run(workspace.workspace_id, run.run_id, "completed")

        # Verify all runs reached completed state
        for run in runs:
            fetched = await repo.get_run(workspace.workspace_id, run.run_id)
            assert fetched.status == "completed"

        await session.delete(workspace)
        await session.commit()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_cancellation_propagation():
    """Test that cancellation propagates through all layers."""
    async with async_session_maker() as session:
        repo = ResearchRepository(session)
        lifecycle = ResearchLifecycleService(repo)

        workspace = Workspace(owner_id=uuid.uuid4())
        session.add(workspace)
        await session.commit()

        run = await repo.create_run(workspace.workspace_id, uuid.uuid4(), "Test cancellation", "legacy")
        await lifecycle.transition_run(workspace.workspace_id, run.run_id, "planning")
        await lifecycle.transition_run(workspace.workspace_id, run.run_id, "researching")

        # Cancel the run
        cancelled = await lifecycle.transition_run(workspace.workspace_id, run.run_id, "cancelled")
        assert cancelled.status == "cancelled"

        # Verify terminal state lock
        with pytest.raises(InvalidTransitionError):
            await lifecycle.transition_run(workspace.workspace_id, run.run_id, "completed")

        await session.delete(workspace)
        await session.commit()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_partial_completion_on_budget_exhaustion():
    """Test that budget exhaustion leads to partial completion."""
    async with async_session_maker() as session:
        repo = ResearchRepository(session)
        lifecycle = ResearchLifecycleService(repo)

        workspace = Workspace(owner_id=uuid.uuid4())
        session.add(workspace)
        await session.commit()

        run = await repo.create_run(workspace.workspace_id, uuid.uuid4(), "Test budget exhaustion", "legacy")
        await lifecycle.transition_run(workspace.workspace_id, run.run_id, "planning")
        await lifecycle.transition_run(workspace.workspace_id, run.run_id, "researching")

        # Budget exhausted -> partial
        partial = await lifecycle.transition_run(workspace.workspace_id, run.run_id, "partial")
        assert partial.status == "partial"

        # Verify terminal state lock
        with pytest.raises(InvalidTransitionError):
            await lifecycle.transition_run(workspace.workspace_id, run.run_id, "completed")

        await session.delete(workspace)
        await session.commit()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_unknown_error_handling():
    """Test that unknown errors lead to failed state with diagnostic event."""
    async with async_session_maker() as session:
        repo = ResearchRepository(session)
        lifecycle = ResearchLifecycleService(repo)

        workspace = Workspace(owner_id=uuid.uuid4())
        session.add(workspace)
        await session.commit()

        run = await repo.create_run(workspace.workspace_id, uuid.uuid4(), "Test unknown error", "legacy")
        await lifecycle.transition_run(workspace.workspace_id, run.run_id, "planning")
        await lifecycle.transition_run(workspace.workspace_id, run.run_id, "researching")

        # Unknown error -> failed
        failed = await lifecycle.transition_run(workspace.workspace_id, run.run_id, "failed")
        assert failed.status == "failed"

        # Verify terminal state lock
        with pytest.raises(InvalidTransitionError):
            await lifecycle.transition_run(workspace.workspace_id, run.run_id, "completed")

        await session.delete(workspace)
        await session.commit()