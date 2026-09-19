import pytest
import pytest_asyncio
import uuid
from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_session_maker
from app.repositories.research import ResearchRepository
from app.services.research.service import ResearchService
from app.models.research import ResearchArtifact
from app.models.workspace import Workspace

pytestmark = pytest.mark.asyncio

@pytest_asyncio.fixture
async def db_session():
    async with async_session_maker() as session:
        yield session

@pytest.fixture
async def workspaces(db_session: AsyncSession):
    ws1 = Workspace(workspace_id=uuid.uuid4(), owner_id=uuid.uuid4())
    db_session.add(ws1)
    await db_session.commit()
    await db_session.refresh(ws1)
    return ws1

@pytest.fixture
def repo(db_session: AsyncSession):
    return ResearchRepository(db_session)

@pytest.fixture
def mock_memory_router():
    router = AsyncMock()
    return router

@pytest.fixture
def mock_graph_repo():
    repo = AsyncMock()
    return repo

@pytest.fixture
def service(repo, mock_memory_router, mock_graph_repo):
    return ResearchService(repo, mock_memory_router, mock_graph_repo)

async def test_promote_memory_candidates(service: ResearchService, repo: ResearchRepository, workspaces: Workspace, mock_memory_router):
    ws1 = workspaces
    
    # Create run
    run = await repo.create_run(workspace_id=ws1.workspace_id, owner_id=ws1.owner_id, objective="Memory Test", engine="test")
    
    # Create a memory_candidate artifact
    # Note: In ResearchRepository.create_artifact, the content argument goes to `content` column. 
    # But in the repo code, it's called `payload`. Let's use payload.
    artifact1 = await repo.create_artifact(
        workspace_id=ws1.workspace_id, 
        run_id=run.run_id, 
        artifact_type="memory_candidate", 
        payload={"text": "This is a memory."}
    )
    
    # Create a non-memory artifact (should be ignored)
    artifact2 = await repo.create_artifact(
        workspace_id=ws1.workspace_id, 
        run_id=run.run_id, 
        artifact_type="other_candidate", 
        payload={"text": "Not a memory."}
    )
    
    promoted_count = await service.promote_memory_candidates(ws1.workspace_id, run.run_id, ws1.owner_id)
    
    assert promoted_count == 1
    mock_memory_router.route_to_memory.assert_called_once()
    
    # Verify the memory schema was constructed correctly
    call_args = mock_memory_router.route_to_memory.call_args[1]
    assert call_args["owner_id"] == ws1.owner_id
    assert call_args["workspace_id"] == ws1.workspace_id
    assert call_args["data"].content == "This is a memory."
    assert call_args["data"].provenance.source_mode == "research"


async def test_promote_graph_candidates(service: ResearchService, repo: ResearchRepository, workspaces: Workspace, mock_graph_repo):
    ws1 = workspaces
    
    # Create run
    run = await repo.create_run(workspace_id=ws1.workspace_id, owner_id=ws1.owner_id, objective="Graph Test", engine="test")
    
    # Create a graph_candidate artifact
    graph_payload = {
        "nodes": [
            {"id": "node1", "label": "Person", "properties": {"name": "Alice"}}
        ],
        "edges": [
            {"source_id": "node1", "target_id": "node2", "type": "KNOWS", "properties": {}}
        ]
    }
    
    artifact1 = await repo.create_artifact(
        workspace_id=ws1.workspace_id, 
        run_id=run.run_id, 
        artifact_type="graph_candidate", 
        payload=graph_payload
    )
    
    promoted_count = await service.promote_graph_candidates(ws1.workspace_id, run.run_id)
    
    assert promoted_count == 1
    mock_graph_repo.project_output_graph.assert_called_once()
    
    # Verify the graph schema was constructed correctly
    call_args = mock_graph_repo.project_output_graph.call_args[1]
    assert call_args["workspace_id"] == ws1.workspace_id
    graph = call_args["graph"]
    assert len(graph.nodes) == 1
    assert graph.nodes[0].id == "node1"
    assert graph.nodes[0].label == "Person"
    assert len(graph.edges) == 1
    assert graph.edges[0].source_id == "node1"
