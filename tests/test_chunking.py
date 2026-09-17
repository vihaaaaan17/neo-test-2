import pytest
from app.services.chunking import ChunkingService

def test_chunking_service_mock_dict():
    chunking = ChunkingService()
    doc_dict = {"text": "Hello world"}
    blocks = chunking.process_docling_output(doc_dict)
    
    assert len(blocks) == 1
    assert blocks[0].block_type == "text"
    assert blocks[0].sequence == 1
    assert blocks[0].text_or_ref == "Hello world"
    
def test_chunking_service_docling_format():
    chunking = ChunkingService()
    doc_dict = {
        "texts": [
            {"text": "First paragraph", "label": "paragraph", "prov": [{"page_no": 1}]},
            {"text": "Second paragraph", "label": "paragraph", "prov": [{"page_no": 2}]}
        ]
    }
    blocks = chunking.process_docling_output(doc_dict)
    
    assert len(blocks) == 2
    assert blocks[0].page_number == 1
    assert blocks[0].sequence == 1
    assert blocks[1].page_number == 2
    assert blocks[1].sequence == 2
