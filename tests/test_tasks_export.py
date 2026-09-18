import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import json
from uuid import uuid4
from app.workers.tasks import export_workspace_job

@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    return redis

@pytest.fixture
def mock_ctx(mock_redis):
    ctx = {
        "redis": mock_redis,
        "s3_client": MagicMock()  # Not used directly in mock but required by job
    }
    return ctx

@pytest.mark.asyncio
@patch("app.services.export.WorkspaceExportService")
@patch("app.workers.tasks.async_session_maker")
async def test_export_workspace_job_success(mock_session_maker, mock_export_service, mock_ctx, mock_redis):
    workspace_id = str(uuid4())
    owner_id = str(uuid4())
    signed_url = "https://test.url/export.zip"
    
    # Mock the service
    mock_service_instance = AsyncMock()
    mock_service_instance.export_to_zip.return_value = signed_url
    mock_export_service.return_value = mock_service_instance
    
    # Mock the DB session context manager
    mock_session = AsyncMock()
    mock_session_maker.return_value.__aenter__.return_value = mock_session

    result = await export_workspace_job(
        mock_ctx,
        workspace_id=workspace_id,
        owner_id=owner_id
    )

    # Asserts
    assert result["status"] == "completed"
    assert result["url"] == signed_url
    assert result["workspace_id"] == workspace_id
    
    mock_service_instance.export_to_zip.assert_called_once()
    
    # Verify Redis events
    assert mock_redis.publish.call_count == 2
    
    # First publish is "starting"
    first_call_args = mock_redis.publish.call_args_list[0][0]
    assert first_call_args[0] == f"export:{workspace_id}"
    event1 = json.loads(first_call_args[1])
    assert event1["status"] == "starting"
    
    # Second publish is "completed"
    second_call_args = mock_redis.publish.call_args_list[1][0]
    event2 = json.loads(second_call_args[1])
    assert event2["status"] == "completed"
    assert event2["url"] == signed_url

@pytest.mark.asyncio
@patch("app.services.export.WorkspaceExportService")
@patch("app.workers.tasks.async_session_maker")
async def test_export_workspace_job_failure(mock_session_maker, mock_export_service, mock_ctx, mock_redis):
    workspace_id = str(uuid4())
    owner_id = str(uuid4())
    
    mock_service_instance = AsyncMock()
    mock_service_instance.export_to_zip.side_effect = Exception("Export failed")
    mock_export_service.return_value = mock_service_instance
    
    mock_session = AsyncMock()
    mock_session_maker.return_value.__aenter__.return_value = mock_session

    result = await export_workspace_job(
        mock_ctx,
        workspace_id=workspace_id,
        owner_id=owner_id
    )

    assert result["status"] == "failed"
    assert "error" in result
    
    # Verify Redis events
    assert mock_redis.publish.call_count == 2
    
    # Second publish is "failed"
    second_call_args = mock_redis.publish.call_args_list[1][0]
    event2 = json.loads(second_call_args[1])
    assert event2["status"] == "failed"
    assert event2["error"] == "Export failed"
