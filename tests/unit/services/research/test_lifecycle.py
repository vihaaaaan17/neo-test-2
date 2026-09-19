import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock
from app.services.research.lifecycle import ResearchLifecycleService, InvalidTransitionError
from app.models.research import ResearchRun, ResearchTask

@pytest.fixture
def mock_repository():
    repo = AsyncMock()
    repo.session = AsyncMock()
    return repo

@pytest.fixture
def lifecycle_service(mock_repository):
    return ResearchLifecycleService(mock_repository)

@pytest.mark.asyncio
async def test_transition_run_valid(lifecycle_service, mock_repository):
    ws_id = uuid.uuid4()
    run_id = uuid.uuid4()
    
    mock_run = MagicMock(spec=ResearchRun)
    mock_run.status = "pending"
    mock_run.run_id = run_id
    mock_repository.get_run.return_value = mock_run
    
    # pending -> planning is valid
    result = await lifecycle_service.transition_run(ws_id, run_id, "planning", {"key": "value"})
    
    assert result.status == "planning"
    mock_repository.session.commit.assert_called_once()
    mock_repository.create_event.assert_called_once_with(
        workspace_id=ws_id,
        run_id=run_id,
        event_type="run.status_changed",
        payload={"from": "pending", "to": "planning", "key": "value"}
    )

@pytest.mark.asyncio
async def test_transition_run_invalid(lifecycle_service, mock_repository):
    ws_id = uuid.uuid4()
    run_id = uuid.uuid4()
    
    mock_run = MagicMock(spec=ResearchRun)
    mock_run.status = "pending"
    mock_run.run_id = run_id
    mock_repository.get_run.return_value = mock_run
    
    # pending -> synthesizing is invalid
    with pytest.raises(InvalidTransitionError, match="Invalid transition"):
        await lifecycle_service.transition_run(ws_id, run_id, "synthesizing")
        
@pytest.mark.asyncio
async def test_transition_run_from_terminal(lifecycle_service, mock_repository):
    ws_id = uuid.uuid4()
    run_id = uuid.uuid4()
    
    mock_run = MagicMock(spec=ResearchRun)
    mock_run.status = "completed"
    mock_run.run_id = run_id
    mock_repository.get_run.return_value = mock_run
    
    with pytest.raises(InvalidTransitionError, match="is in terminal state"):
        await lifecycle_service.transition_run(ws_id, run_id, "planning")

@pytest.mark.asyncio
async def test_transition_task_valid(lifecycle_service, mock_repository):
    ws_id = uuid.uuid4()
    run_id = uuid.uuid4()
    task_id = uuid.uuid4()
    
    mock_task = MagicMock(spec=ResearchTask)
    mock_task.status = "pending"
    mock_task.task_id = task_id
    mock_repository.get_task.return_value = mock_task
    
    # pending -> running is valid
    result = await lifecycle_service.transition_task(ws_id, run_id, task_id, "running")
    
    assert result.status == "running"
    mock_repository.session.commit.assert_called_once()
    mock_repository.create_event.assert_called_once_with(
        workspace_id=ws_id,
        run_id=run_id,
        task_id=task_id,
        event_type="task.status_changed",
        payload={"from": "pending", "to": "running"}
    )

@pytest.mark.asyncio
async def test_transition_task_invalid(lifecycle_service, mock_repository):
    ws_id = uuid.uuid4()
    run_id = uuid.uuid4()
    task_id = uuid.uuid4()
    
    mock_task = MagicMock(spec=ResearchTask)
    mock_task.status = "pending"
    mock_task.task_id = task_id
    mock_repository.get_task.return_value = mock_task
    
    # pending -> completed is invalid without running first
    with pytest.raises(InvalidTransitionError, match="Invalid transition"):
        await lifecycle_service.transition_task(ws_id, run_id, task_id, "completed")
