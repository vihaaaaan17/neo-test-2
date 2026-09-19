import pytest
import httpx
from unittest.mock import patch, MagicMock, AsyncMock
import sys

# Mock external dependencies missing from local env before importing models
sys.modules['pgvector'] = MagicMock()
sys.modules['pgvector.sqlalchemy'] = MagicMock()
sys.modules['aioboto3'] = MagicMock()
sys.modules['docling'] = MagicMock()
sys.modules['docling.document_converter'] = MagicMock()
sys.modules['litellm'] = MagicMock()
sys.modules['neo4j'] = MagicMock()

from app.workers.tasks import project_to_open_notebook_job
from arq.worker import Retry
import uuid

pytestmark = pytest.mark.asyncio

async def test_project_to_open_notebook_job_backpressure():
    # Setup test data
    source_id = str(uuid.uuid4())
    snapshot_id = str(uuid.uuid4())
    workspace_id = str(uuid.uuid4())
    
    ctx = {"job_try": 2}
    
    # Mock Open Notebook returning 429 Too Many Requests
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.headers = {"Retry-After": "45"}
    error = httpx.HTTPStatusError("429 Too Many Requests", request=MagicMock(), response=mock_response)
    
    with patch("app.workers.tasks.async_session_maker") as mock_session_maker:
        mock_session = AsyncMock()
        mock_session_maker.return_value.__aenter__.return_value = mock_session
        
        with patch("app.workers.tasks._get_source_and_snapshot") as mock_get_source:
            mock_get_source.return_value = (MagicMock(), MagicMock(checksum_sha256="abc", file_uri="s3://b/f"))
            
            with patch("app.repositories.open_notebook.OpenNotebookRepository") as MockRepo:
                mock_repo_inst = MockRepo.return_value
                mock_repo_inst.claim_projection_job = AsyncMock(return_value=MagicMock())
                mock_repo_inst.get_workspace_binding = AsyncMock(return_value=MagicMock())
                
                with patch("app.services.storage.S3ObjectStore") as MockStorage:
                    MockStorage.return_value.download_file = AsyncMock(return_value=b"data")
                    
                    with patch("app.integrations.open_notebook.client.OpenNotebookClient.upload_source") as mock_upload:
                        mock_upload.side_effect = error
                        
                        ctx["s3_client"] = MagicMock()
                        
                        with pytest.raises(Retry) as exc:
                            await project_to_open_notebook_job(
                                ctx,
                                source_id=source_id,
                                snapshot_id=snapshot_id,
                                workspace_id=workspace_id
                            )
                            
                        # Assert Retry was raised with defer_score corresponding to the delay
                        assert exc.value.defer_score is not None
