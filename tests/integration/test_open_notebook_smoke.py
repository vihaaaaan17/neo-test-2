import os
import pytest
import httpx
from app.core.config import settings

@pytest.mark.open_notebook
@pytest.mark.asyncio
async def test_open_notebook_ingestion_and_search():
    base_url = settings.OPEN_NOTEBOOK_BASE_URL
    password = os.getenv("OPEN_NOTEBOOK_PASSWORD")
    
    headers = {}
    if password:
        headers["Authorization"] = f"Bearer {password}"
        
    async with httpx.AsyncClient(base_url=base_url, headers=headers, timeout=10.0) as client:
        # 1. Ingest Markdown file using /api/sources
        fixture_path = "tests/fixtures/open_notebook/sample.md"
        assert os.path.exists(fixture_path), f"Fixture not found at {fixture_path}"
        
        with open(fixture_path, "rb") as f:
            files = {"file": ("sample.md", f, "text/markdown")}
            res = await client.post("/api/sources", files=files)
            
        assert res.status_code == 200, f"Source upload failed: {res.text}"
        source = res.json()
        assert "id" in source
        
        # 2. Ask/Search query using /api/search
        search_data = {
            "query": "ingestion tests",
            "type": "text",
            "limit": 5,
            "search_sources": True,
            "search_notes": False
        }
        search_res = await client.post("/api/search", json=search_data)
        assert search_res.status_code == 200, f"Search failed: {search_res.text}"
        
        search_results = search_res.json().get("results", [])
        assert isinstance(search_results, list)
