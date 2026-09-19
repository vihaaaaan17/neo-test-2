import pytest
import pytest_asyncio
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_session_maker
from app.repositories.open_notebook import OpenNotebookRepository
from app.models.open_notebook_binding import OpenNotebookWorkspaceBinding, OpenNotebookSourceBinding
from app.models.workspace import Workspace
from app.models.source import Source, SourceSnapshot

@pytest_asyncio.fixture
async def db_session():
    async with async_session_maker() as session:
        yield session

@pytest_asyncio.fixture
async def open_notebook_repo(db_session: AsyncSession):
    return OpenNotebookRepository(db_session)

@pytest_asyncio.fixture
async def sample_workspace(db_session: AsyncSession):
    ws = Workspace(
        workspace_id=uuid.uuid4(),
        owner_id=uuid.uuid4(),
        status="active"
    )
    db_session.add(ws)
    await db_session.commit()
    await db_session.refresh(ws)
    return ws

@pytest_asyncio.fixture
async def sample_source(db_session: AsyncSession, sample_workspace: Workspace):
    src = Source(
        source_id=uuid.uuid4(),
        workspace_id=sample_workspace.workspace_id,
        owner_id=sample_workspace.owner_id,
        source_type="document",
        processing_status="completed"
    )
    db_session.add(src)
    await db_session.commit()
    await db_session.refresh(src)
    return src

@pytest_asyncio.fixture
async def sample_snapshot(db_session: AsyncSession, sample_source: Source):
    snap = SourceSnapshot(
        snapshot_id=uuid.uuid4(),
        source_id=sample_source.source_id,
        file_uri="s3://test/test.txt",
        filename="test.txt",
        size=1024,
        checksum_sha256="fakechecksum"
    )
    db_session.add(snap)
    await db_session.commit()
    await db_session.refresh(snap)
    return snap

@pytest.mark.asyncio
async def test_workspace_binding_creation(open_notebook_repo: OpenNotebookRepository, sample_workspace: Workspace):
    notebook_id = f"nb_{uuid.uuid4().hex}"
    binding = await open_notebook_repo.create_workspace_binding(sample_workspace.workspace_id, notebook_id)
    assert binding is not None
    assert binding.workspace_id == sample_workspace.workspace_id
    assert binding.open_notebook_notebook_id == notebook_id

    # Test idempotency / duplicate creation returns same binding
    duplicate_binding = await open_notebook_repo.create_workspace_binding(sample_workspace.workspace_id, "some_other_id")
    assert duplicate_binding.open_notebook_notebook_id == notebook_id

@pytest.mark.asyncio
async def test_claim_projection_job_success(open_notebook_repo: OpenNotebookRepository, sample_snapshot: SourceSnapshot):
    binding = await open_notebook_repo.claim_projection_job(
        sample_snapshot.source_id,
        sample_snapshot.snapshot_id,
        sample_snapshot.checksum_sha256
    )
    assert binding is not None
    assert binding.projection_status == "PROJECTING"

@pytest.mark.asyncio
async def test_claim_projection_job_concurrency(open_notebook_repo: OpenNotebookRepository, sample_snapshot: SourceSnapshot):
    # First claim succeeds
    binding1 = await open_notebook_repo.claim_projection_job(
        sample_snapshot.source_id,
        sample_snapshot.snapshot_id,
        sample_snapshot.checksum_sha256
    )
    assert binding1 is not None

    # Second concurrent claim for same snapshot fails safely
    binding2 = await open_notebook_repo.claim_projection_job(
        sample_snapshot.source_id,
        sample_snapshot.snapshot_id,
        sample_snapshot.checksum_sha256
    )
    assert binding2 is None

@pytest.mark.asyncio
async def test_update_projection_status(open_notebook_repo: OpenNotebookRepository, sample_snapshot: SourceSnapshot):
    binding = await open_notebook_repo.claim_projection_job(
        sample_snapshot.source_id,
        sample_snapshot.snapshot_id,
        sample_snapshot.checksum_sha256
    )
    
    on_src_id = f"on_src_{uuid.uuid4().hex}"
    updated_binding = await open_notebook_repo.update_projection_status(
        source_id=sample_snapshot.source_id,
        snapshot_id=sample_snapshot.snapshot_id,
        status="ACTIVE",
        open_notebook_source_id=on_src_id
    )
    
    assert updated_binding is not None
    assert updated_binding.projection_status == "ACTIVE"
    assert updated_binding.open_notebook_source_id == on_src_id
    assert updated_binding.projected_at is not None
