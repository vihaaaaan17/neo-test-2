import tempfile
import os
import asyncio
from typing import Any
try:
    from docling.document_converter import DocumentConverter
except ImportError:
    DocumentConverter = None
from app.services.storage import ObjectStoreProtocol

class DocumentParser:
    def __init__(self, storage: ObjectStoreProtocol):
        self.storage = storage

    async def parse_document(self, file_uri: str) -> dict[str, Any]:
        """
        Downloads a document from Object Storage and parses it using docling.
        Returns a structured dictionary representation of the document.
        """
        # 1. Download file bytes
        file_bytes = await self.storage.download_file(file_uri)
        
        # 2. Write to secure temporary file
        fd, temp_path = tempfile.mkstemp(suffix=".pdf")
        try:
            with os.fdopen(fd, 'wb') as f:
                f.write(file_bytes)
            
            # 3. Parse in background thread to avoid blocking event loop
            doc_dict = await asyncio.to_thread(self._run_docling, temp_path)
            return doc_dict
        finally:
            # 4. Clean up
            os.remove(temp_path)

    def _run_docling(self, file_path: str) -> dict[str, Any]:
        converter = DocumentConverter()
        result = converter.convert(file_path)
        return result.document.export_to_dict()
