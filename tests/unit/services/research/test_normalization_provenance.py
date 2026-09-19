import pytest
import uuid
from unittest.mock import AsyncMock
from app.services.research.normalization import ResearchNormalizationService
from app.services.research.provenance import ResearchProvenanceService

def test_normalization_service_url():
    service = ResearchNormalizationService()
    
    # Test lowercase domain and scheme
    url1 = "HTTP://Example.COM/Path"
    url2 = "http://example.com/Path"
    
    assert service.normalize_url(url1) == service.normalize_url(url2)
    
    # Test query param sorting
    url3 = "https://a.com/?b=2&a=1"
    url4 = "https://a.com/?a=1&b=2"
    
    assert service.normalize_url(url3) == service.normalize_url(url4)
    
def test_normalization_fingerprint():
    service = ResearchNormalizationService()
    
    url = "https://example.com/?q=test"
    content = "   This  is \n some evidence.  "
    
    fp1 = service.generate_fingerprint(content, url)
    fp2 = service.generate_fingerprint("This is some evidence.", url)
    
    assert fp1 == fp2
    
    # Same content, different url -> different fp
    fp3 = service.generate_fingerprint("This is some evidence.", "https://example.com")
    assert fp1 != fp3

@pytest.mark.asyncio
async def test_provenance_unresolved():
    session_mock = AsyncMock()
    # Mock execute returning nothing
    from unittest.mock import MagicMock
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    session_mock.execute.return_value = result_mock
    
    service = ResearchProvenanceService(session_mock)
    
    ws_id = uuid.uuid4()
    citation = {"url": "https://unknown.com", "title": "Unknown"}
    
    source_id, raw = await service.resolve_source(ws_id, citation)
    
    assert source_id is None
    assert raw == citation

@pytest.mark.asyncio
async def test_provenance_resolved():
    session_mock = AsyncMock()
    # Mock execute returning a source_id
    from unittest.mock import MagicMock
    mock_source_id = uuid.uuid4()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = mock_source_id
    session_mock.execute.return_value = result_mock
    
    service = ResearchProvenanceService(session_mock)
    
    ws_id = uuid.uuid4()
    citation = {"url": "https://known.com", "title": "Known"}
    
    source_id, raw = await service.resolve_source(ws_id, citation)
    
    assert source_id == mock_source_id
    assert raw is None

@pytest.mark.asyncio
async def test_provenance_no_url():
    session_mock = AsyncMock()
    service = ResearchProvenanceService(session_mock)
    
    ws_id = uuid.uuid4()
    citation = {"title": "Book Title", "author": "John Doe"}
    
    source_id, raw = await service.resolve_source(ws_id, citation)
    
    assert source_id is None
    assert raw == citation
