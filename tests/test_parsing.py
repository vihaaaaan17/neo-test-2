import pytest
from unittest.mock import patch, MagicMock
from app.services.parsing import DocumentParser
from app.services.storage import ObjectStoreProtocol

class MockObjectStore(ObjectStoreProtocol):
    async def upload_file(self, workspace_id, file_bytes, filename):
        return f"s3://mock-bucket/{workspace_id}/mock-uuid-{filename}"
        
    async def download_file(self, file_uri: str) -> bytes:
        return b"mock pdf content"

@pytest.mark.asyncio
async def test_parse_document():
    storage = MockObjectStore()
    parser = DocumentParser(storage)
    
    with patch("app.services.parsing.DocumentConverter") as mock_converter_class:
        mock_instance = mock_converter_class.return_value
        mock_result = MagicMock()
        mock_result.document.export_to_dict.return_value = {"text": "mock extracted text"}
        mock_instance.convert.return_value = mock_result
        
        result = await parser.parse_document("s3://mock-bucket/mock-key")
        
        assert result == {"text": "mock extracted text"}
        mock_instance.convert.assert_called_once()
        
        called_path = mock_instance.convert.call_args[0][0]
        assert called_path.endswith(".pdf")
