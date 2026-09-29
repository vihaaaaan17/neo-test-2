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
        
        # Simulate final report generation persistence
        async with async_session_maker() as session:
            repo = ResearchRepository(session)
            await repo.create_report(workspace_id, run_id, objective, "Mock final report")
            await repo.create_artifact(
                workspace_id, run_id, "memory_candidate", {"text": "Mock final report", "domain": "deep_research"}
            )
            
        yield {"status": "synthesizing", "message": "done", "summary": "Mock final report"}
        
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
    Worker -> ODR Adapter (Mock) -> Postgres -> Memory Promotion.
    """
    # 1. Setup Data
    workspace_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    run_id = uuid.uuid4()
    
    workspace = Workspace(workspace_id=workspace_id, owner_id=owner_id)
    db_session.add(workspace)
    await db_session.flush()
    
    run = ResearchRun(run_id=run_id, workspace_id=workspace_id, owner_id=owner_id, objective="Test Objective", engine="odr", status="pending")
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
    
    # Check artifacts and reports
    report_result = await db_session.execute(select(ResearchReport).where(ResearchReport.run_id == run_id))
    report = report_result.scalar_one_or_none()
    assert report is not None
    assert report.content == "Mock final report"
    
    artifact_result = await db_session.execute(select(ResearchArtifact).where(ResearchArtifact.run_id == run_id))
    artifacts = artifact_result.scalars().all()
    assert len(artifacts) == 1
    assert artifacts[0].type == "memory_candidate"
    
    # Check memory promotion via Promotion Service
    from app.services.research.service import ResearchService
    from app.services.memory_router import MemoryRouter
    from app.repositories.knowledge import KnowledgeRepository

    research_svc = ResearchService(
        research_repo=ResearchRepository(db_session),
        memory_router=MemoryRouter(repository=KnowledgeRepository(db_session)),
        graph_repo=None
    )
    promoted = await research_svc.promote_memory_candidates(workspace_id=workspace_id, run_id=run_id, owner_id=owner_id)
    assert promoted >= 1

    mem_result = await db_session.execute(select(KnowledgeMemory).where(KnowledgeMemory.workspace_id == workspace_id))
    memories = mem_result.scalars().all()
    assert len(memories) >= 1
    
    memory = memories[-1]
    assert memory.domain == "deep_research"
