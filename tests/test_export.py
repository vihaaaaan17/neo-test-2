import pytest
import zipfile
import io
import json
import pandas as pd
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from app.services.export import WorkspaceExportService
from app.models.workspace import Workspace
from app.models.source import Source, SourceSnapshot
from app.models.knowledge import KnowledgeMemory
from app.models.episodic import EpisodicMemory
from app.models.block import DocumentBlock

@pytest.fixture
def mock_object_store():
    store = AsyncMock()
    store.upload_file.return_value = "s3://test-bucket/test.zip"
    store.generate_presigned_url.return_value = "https://presigned.url/test.zip"
    return store

@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    
    def make_mock_result(items):
        mock_res = MagicMock()
        scalars_mock = MagicMock()
        if not items:
            scalars_mock.first.return_value = None
            scalars_mock.all.return_value = []
            scalars_mock.__iter__.return_value = iter([])
        else:
            scalars_mock.first.return_value = items[0]
            scalars_mock.all.return_value = items
            scalars_mock.__iter__.return_value = iter(items)
        mock_res.scalars.return_value = scalars_mock
        return mock_res
        
    workspace_id = uuid4()
    
    workspace = Workspace(workspace_id=workspace_id, owner_id=uuid4(), status="active")
    source = Source(source_id=uuid4(), workspace_id=workspace_id, owner_id=uuid4(), source_type="document")
    knowledge = KnowledgeMemory(knowledge_id=uuid4(), workspace_id=workspace_id, owner_id=uuid4(), knowledge_type="fact", content="Test knowledge", status="active", provenance={})
    episodic = EpisodicMemory(episode_id=uuid4(), workspace_id=workspace_id, owner_id=uuid4(), event_type="log", summary="Test episode")
    snapshot_id = uuid4()
    block = DocumentBlock(block_id=uuid4(), source_id=source.source_id, snapshot_id=snapshot_id, block_type="text", text_or_ref="Test chunk", sequence=1, embedding=[0.1, 0.2, 0.3])

    async def mock_execute(stmt):
        stmt_str = str(stmt)
        if "workspace" in stmt_str and "source" not in stmt_str and "knowledge" not in stmt_str and "episodic" not in stmt_str and "block" not in stmt_str:
            return make_mock_result([workspace])
        elif "source" in stmt_str and "block" not in stmt_str:
            return make_mock_result([source])
        elif "knowledge" in stmt_str:
            return make_mock_result([knowledge])
        elif "episodic" in stmt_str:
            return make_mock_result([episodic])
        elif "block" in stmt_str:
            return make_mock_result([block])
        return make_mock_result([])

    session.execute.side_effect = mock_execute
    return session, workspace_id

@pytest.mark.asyncio
async def test_workspace_export_service(mock_db_session, mock_object_store):
    session, workspace_id = mock_db_session
    service = WorkspaceExportService(db=session, object_store=mock_object_store)
    
    url = await service.export_to_zip(workspace_id)
    
    assert url == "https://presigned.url/test.zip"
    
    mock_object_store.upload_file.assert_called_once()
    call_args = mock_object_store.upload_file.call_args[0]
    assert call_args[0] == workspace_id
    assert call_args[2] == f"export_{workspace_id}.zip"
    
    zip_bytes = call_args[1]
    assert isinstance(zip_bytes, bytes)
    
    zip_buffer = io.BytesIO(zip_bytes)
    with zipfile.ZipFile(zip_buffer, "r") as zf:
        file_list = zf.namelist()
        assert "metadata.json" in file_list
        assert "chunks.parquet" in file_list
        
        metadata_bytes = zf.read("metadata.json")
        metadata = json.loads(metadata_bytes)
        assert metadata["workspace"]["status"] == "active"
        assert len(metadata["sources"]) == 1
        assert metadata["sources"][0]["source_type"] == "document"
        assert metadata["knowledge"][0]["content"] == "Test knowledge"
        
        parquet_bytes = zf.read("chunks.parquet")
        parquet_buffer = io.BytesIO(parquet_bytes)
        df = pd.read_parquet(parquet_buffer)
        
        assert len(df) == 1
        assert df.iloc[0]["text_or_ref"] == "Test chunk"
        assert df.iloc[0]["sequence"] == 1
        assert list(df.iloc[0]["embedding"]) == [0.1, 0.2, 0.3]
