import pytest
import pytest_asyncio
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_session_maker
from app.repositories.research import ResearchRepository
from app.models.research import ResearchRun, ResearchTask, ResearchEvidence, ResearchArtifact, ResearchReport, ResearchUsage, ResearchEvent
from app.models.workspace import Workspace

pytestmark = pytest.mark.asyncio

@pytest_asyncio.fixture
async def db_session():
    async with async_session_maker() as session:
        yield session
@pytest.fixture
async def workspaces(db_session: AsyncSession):
    ws1 = Workspace(workspace_id=uuid.uuid4(), owner_id=uuid.uuid4())
    ws2 = Workspace(workspace_id=uuid.uuid4(), owner_id=uuid.uuid4())
    db_session.add(ws1)
    db_session.add(ws2)
    await db_session.commit()
    await db_session.refresh(ws1)
    await db_session.refresh(ws2)
    return ws1, ws2

@pytest.fixture
def repo(db_session: AsyncSession):
    return ResearchRepository(db_session)

async def test_create_and_get_run(repo: ResearchRepository, workspaces):
    ws1, _ = workspaces
    run = await repo.create_run(workspace_id=ws1.workspace_id, owner_id=ws1.owner_id, objective="Test", engine="test_engine")
    
    assert run.run_id is not None
    assert run.workspace_id == ws1.workspace_id
    
    fetched = await repo.get_run(ws1.workspace_id, run.run_id)
    assert fetched is not None
    assert fetched.run_id == run.run_id

async def test_workspace_isolation(repo: ResearchRepository, workspaces):
    ws1, ws2 = workspaces
    run = await repo.create_run(workspace_id=ws1.workspace_id, owner_id=ws1.owner_id, objective="Test", engine="test_engine")
    
    # Try to access run from another workspace
    fetched = await repo.get_run(ws2.workspace_id, run.run_id)
    assert fetched is None
    
    # Try to create a task for this run using the wrong workspace
    with pytest.raises(ValueError, match="not found in workspace"):
        await repo.create_task(workspace_id=ws2.workspace_id, run_id=run.run_id, objective="Task")

    # Try to create evidence for this run using the wrong workspace
    with pytest.raises(ValueError, match="not found in workspace"):
        await repo.create_evidence(workspace_id=ws2.workspace_id, run_id=run.run_id, content="Content")

async def test_crud_operations(repo: ResearchRepository, workspaces):
    ws1, _ = workspaces
    
    # Create Run
    run = await repo.create_run(workspace_id=ws1.workspace_id, owner_id=ws1.owner_id, objective="Test", engine="test_engine")
    
    # Create Task
    task = await repo.create_task(workspace_id=ws1.workspace_id, run_id=run.run_id, objective="Task")
    assert task.task_id is not None
    fetched_task = await repo.get_task(ws1.workspace_id, run.run_id, task.task_id)
    assert fetched_task is not None
    
    # Create Evidence
    evidence = await repo.create_evidence(workspace_id=ws1.workspace_id, run_id=run.run_id, task_id=task.task_id, content="Evidence", tags=["test"])
    assert evidence.evidence_id is not None
    fetched_evidence = await repo.get_evidence(ws1.workspace_id, run.run_id, evidence.evidence_id)
    assert fetched_evidence is not None
    
    # Create Artifact
    artifact = await repo.create_artifact(workspace_id=ws1.workspace_id, run_id=run.run_id, task_id=task.task_id, artifact_type="memory_candidate", payload={"key": "value"})
    assert artifact.artifact_id is not None
    fetched_artifact = await repo.get_artifact(ws1.workspace_id, run.run_id, artifact.artifact_id)
    assert fetched_artifact is not None
    assert fetched_artifact.payload["key"] == "value"
    
    # Create Report
    report = await repo.create_report(workspace_id=ws1.workspace_id, run_id=run.run_id, objective="Report Objective", content="Report Content")
    assert report.report_id is not None
    fetched_report = await repo.get_report(ws1.workspace_id, run.run_id, report.report_id)
    assert fetched_report is not None
    
    # Create Usage
    usage = await repo.create_usage(workspace_id=ws1.workspace_id, run_id=run.run_id, task_id=task.task_id, model_calls=5)
    assert usage.usage_id is not None
    fetched_usage = await repo.get_usage(ws1.workspace_id, run.run_id, usage.usage_id)
    assert fetched_usage is not None
    assert fetched_usage.model_calls == 5
    
    # Create Event
    event = await repo.create_event(workspace_id=ws1.workspace_id, run_id=run.run_id, task_id=task.task_id, event_type="research.started", payload={"status": "running"})
    assert event.event_id is not None
    events = await repo.get_events_for_run(ws1.workspace_id, run.run_id)
    assert len(events) == 1
    assert events[0].event_type == "research.started"
