import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime, timezone

from app.models.workspace import Workspace, WorkspaceCommit
from app.repositories.workspace import WorkspaceRepository


@pytest.mark.asyncio
async def test_create_commit_with_manifest():
    workspace_id = uuid4()
    parent_id = uuid4()
    k1 = uuid4()
    k2 = uuid4()
    artifact_1 = uuid4()

    manifest = {
        "knowledge_memory_ids": [str(k1), str(k2)],
        "accepted_artifact_ids": [str(artifact_1)],
        "output_graph_version": "v1.2",
        "active_hypothesis_ids": [],
        "scratchpad_checkpoint": "sp_chk_01",
        "conversation_checkpoint": "conv_chk_01",
        "base_research_run_ids": [],
        "schema_version": 1
    }

    session = AsyncMock()
    session.add = MagicMock()
    repo = WorkspaceRepository(session)

    commit = await repo.create_commit_with_manifest(
        workspace_id=workspace_id,
        parent_id=parent_id,
        active_knowledge_ids=[k1, k2],
        manifest=manifest
    )

    assert commit.workspace_id == workspace_id
    assert commit.parent_id == parent_id
    assert commit.active_knowledge_ids == [str(k1), str(k2)]
    assert commit.manifest["output_graph_version"] == "v1.2"
    assert commit.manifest["accepted_artifact_ids"] == [str(artifact_1)]
    assert session.add.called
    assert session.commit.called


@pytest.mark.asyncio
async def test_rollback_workspace_atomic_increments_epoch():
    workspace_id = uuid4()
    owner_id = uuid4()
    commit_id = uuid4()

    mock_workspace = Workspace(
        workspace_id=workspace_id,
        owner_id=owner_id,
        status="active",
        timeline_epoch=3,
        active_commit_id=uuid4(),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    mock_commit = WorkspaceCommit(
        commit_id=commit_id,
        workspace_id=workspace_id,
        active_knowledge_ids=[],
        manifest={"schema_version": 1},
        created_at=datetime.now(timezone.utc)
    )

    session = AsyncMock()
    # First call: select workspace for update
    # Second call: get commit
    mock_ws_res = MagicMock()
    mock_ws_res.scalars.return_value.first.return_value = mock_workspace

    mock_commit_res = MagicMock()
    mock_commit_res.scalars.return_value.first.return_value = mock_commit

    session.execute.side_effect = [mock_ws_res, mock_commit_res]

    repo = WorkspaceRepository(session)
    updated_ws, new_epoch = await repo.rollback_workspace_atomic(workspace_id, commit_id, owner_id)

    assert updated_ws is not None
    assert new_epoch == 4
    assert updated_ws.timeline_epoch == 4
    assert updated_ws.active_commit_id == commit_id
    assert session.commit.called


@pytest.mark.asyncio
async def test_rollback_workspace_atomic_commit_not_found():
    workspace_id = uuid4()
    owner_id = uuid4()
    commit_id = uuid4()

    mock_workspace = Workspace(
        workspace_id=workspace_id,
        owner_id=owner_id,
        status="active",
        timeline_epoch=1
    )

    session = AsyncMock()
    mock_ws_res = MagicMock()
    mock_ws_res.scalars.return_value.first.return_value = mock_workspace

    mock_commit_res = MagicMock()
    mock_commit_res.scalars.return_value.first.return_value = None

    session.execute.side_effect = [mock_ws_res, mock_commit_res]

    repo = WorkspaceRepository(session)
    updated_ws, new_epoch = await repo.rollback_workspace_atomic(workspace_id, commit_id, owner_id)

    assert updated_ws is None
    assert new_epoch == 0


@pytest.mark.asyncio
async def test_verify_timeline_epoch():
    workspace_id = uuid4()

    session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = 5
    session.execute.return_value = mock_res

    repo = WorkspaceRepository(session)

    # Matching epoch
    is_valid = await repo.verify_timeline_epoch(workspace_id, 5)
    assert is_valid is True

    # Stale epoch
    is_stale = await repo.verify_timeline_epoch(workspace_id, 4)
    assert is_stale is False
