import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from app.workers.tasks import (
    project_to_open_notebook_job,
    delete_open_notebook_source_job,
    delete_open_notebook_workspace_job
)

@pytest.mark.asyncio
async def test_project_to_open_notebook_job_not_found():
    ctx = {"s3_client": AsyncMock()}
    result = await project_to_open_notebook_job(
        ctx,
        source_id=str(uuid4()),
        snapshot_id=str(uuid4()),
        workspace_id=str(uuid4())
    )
    assert result["status"] == "not_found"

@pytest.mark.asyncio
async def test_delete_open_notebook_source_job_no_binding():
    ctx = {}
    result = await delete_open_notebook_source_job(
        ctx,
        source_id=str(uuid4()),
        snapshot_id=str(uuid4())
    )
    assert result["status"] == "skipped"
    assert result["reason"] == "no_binding"

@pytest.mark.asyncio
async def test_delete_open_notebook_workspace_job_no_binding():
    ctx = {}
    result = await delete_open_notebook_workspace_job(
        ctx,
        workspace_id=str(uuid4())
    )
    assert result["status"] == "skipped"
    assert result["reason"] == "no_binding"
