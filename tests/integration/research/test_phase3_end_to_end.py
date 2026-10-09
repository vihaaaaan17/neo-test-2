import pytest
import uuid
import asyncio
from typing import AsyncGenerator, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import async_session_maker
from app.integrations.research_engine.engine import ResearchEngine
from app.integrations.research_engine.factory import ResearchEngineFactory
from app.workers.tasks import run_research_agent_job
from app.models.research import ResearchRun, ResearchReport, ResearchArtifact
from app.models.knowledge import KnowledgeMemory
from app.models.workspace import Workspace
from app.repositories.research import ResearchRepository
from app.services.research.lifecycle import ResearchLifecycleService

class MockODREngine(ResearchEngine):
    async def astream_events(self, run_id: uuid.UUID, workspace_id: uuid.UUID, objective: str, research_context: Any = None, **kwargs) -> AsyncGenerator[dict[str, Any], None]:
        yield {"status": "starting", "message": "starting"}

        # New contract: the engine hands the report to the worker as data; the worker persists it.
        yield {"status": "synthesizing", "message": "done"}
        yield {"status": "turn_response", "text": "Mock final report"}

    async def cancel(self) -> None:
        pass

@pytest.fixture
def mock_engine_factory(monkeypatch):
    def mock_get_engine(*args, **kwargs):
        return MockODREngine()
    monkeypatch.setattr(ResearchEngineFactory, "get_engine", mock_get_engine)

@pytest.mark.asyncio
async def test_phase3_end_to_end_flow(mock_engine_factory, db_session: AsyncSession):
    """
    Tests the End-to-End flow of Phase 3 Research Engine.
    Worker -> EngineRouter -> ODR Adapter (Mock) -> Postgres; no automatic report, candidate or promotion.
    """
    # 1. Setup Data
    workspace_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    run_id = uuid.uuid4()
    
    workspace = Workspace(workspace_id=workspace_id, owner_id=owner_id)
    db_session.add(workspace)
    await db_session.flush()
    
    run = ResearchRun(run_id=run_id, workspace_id=workspace_id, owner_id=owner_id, objective="Test Objective", engine="open_deep_research", status="pending")
    db_session.add(run)
    await db_session.commit()
    
    # 2. Run the Worker Job
    ctx = {
        "job_id": "test_job_123",
        "redis": None,
        "llm_call": lambda prompt, **kwargs: "Mock LLM Response"
    }
    
    result = await run_research_agent_job(ctx, workspace_id=str(workspace_id), objective="Test Objective", run_id=str(run_id))
    
    # 3. Assertions
    assert result["status"] == "completed"
    
    # Check DB transitions
    await db_session.refresh(run)
    assert run.status == "completed", "ResearchRun should be transitioned to completed by the worker task"
    
    # Chapter 6: an ordinary research turn creates no ResearchReport and no promotion candidate...
    report_result = await db_session.execute(select(ResearchReport).where(ResearchReport.run_id == run_id))
    assert report_result.scalars().all() == []
    artifact_result = await db_session.execute(select(ResearchArtifact).where(ResearchArtifact.run_id == run_id))
    assert artifact_result.scalars().all() == []

    # ...and the router recorded exactly one attempt, by the explicitly requested engine.
    from app.models.research import ResearchEngineAttempt
    attempts = (await db_session.execute(
        select(ResearchEngineAttempt).where(ResearchEngineAttempt.run_id == run_id)
    )).scalars().all()
    assert [(a.engine, a.trigger, a.status) for a in attempts] == [("open_deep_research", "explicit", "answered")]
    await db_session.refresh(run)
    assert run.current_attempt_id == attempts[0].attempt_id

    # Nothing reached knowledge memory.
    mem_result = await db_session.execute(select(KnowledgeMemory).where(KnowledgeMemory.workspace_id == workspace_id))
    assert mem_result.scalars().all() == []
