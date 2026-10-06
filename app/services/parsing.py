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
        # Preserve the real extension so Docling picks the right backend (and plain text is detected).
        suffix = os.path.splitext(file_uri.split("?", 1)[0])[1].lower() or ".pdf"
        fd, temp_path = tempfile.mkstemp(suffix=suffix)
        try:
            with os.fdopen(fd, 'wb') as f:
                f.write(file_bytes)
            
            # 3. Parse in background thread to avoid blocking event loop
            doc_dict = await asyncio.to_thread(self._run_docling, temp_path)
            return doc_dict
        finally:
            # 4. Clean up
            os.remove(temp_path)

    PLAIN_TEXT_SUFFIXES = (".txt", ".text", ".log")

    def _run_docling(self, file_path: str) -> dict[str, Any]:
        if DocumentConverter is None or file_path.lower().endswith(self.PLAIN_TEXT_SUFFIXES):
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    return {"text": f.read()}
            except Exception:
                return {"text": ""}
        converter = DocumentConverter()
        result = converter.convert(file_path)
        return result.document.export_to_dict()
