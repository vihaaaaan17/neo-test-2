import pytest
from httpx import AsyncClient, ASGITransport, Response, Request
from fastapi import HTTPException
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from app.integrations.open_notebook.client import OpenNotebookClient
from app.integrations.open_notebook.ground_engine import OpenNotebookGroundEngine
from uuid import uuid4

pytestmark = pytest.mark.asyncio

async def test_client_error_translation_400():
    client = OpenNotebookClient()
    
    # Mock httpx.AsyncClient.get to raise a 400 error
    with patch("httpx.AsyncClient.get") as mock_get:
        # Create a mock response
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        
        # Create the exception
        mock_error = httpx.HTTPStatusError("400 Bad Request", request=MagicMock(), response=mock_response)
        mock_get.side_effect = mock_error
        
        try:
            await client.get_health()
            assert False, "Should have raised HTTPException"
        except HTTPException as e:
            assert e.status_code == 400
            assert e.detail == "ground_validation_error"

async def test_client_error_translation_500():
    client = OpenNotebookClient()
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        
        mock_error = httpx.HTTPStatusError("500 Internal Error", request=MagicMock(), response=mock_response)
        mock_get.side_effect = mock_error
        
        try:
            await client.get_health()
            assert False, "Should have raised HTTPException"
        except HTTPException as e:
            assert e.status_code == 502
            assert e.detail == "ground_execution_failed"

async def test_client_error_translation_timeout():
    client = OpenNotebookClient()
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_error = httpx.RequestError("Timeout")
        mock_get.side_effect = mock_error
        
        try:
            await client.get_health()
            assert False, "Should have raised HTTPException"
        except HTTPException as e:
            assert e.status_code == 503
            assert e.detail == "ground_dependency_unavailable"

async def test_engine_zero_evidence_rejection():
    engine = OpenNotebookGroundEngine()
    
    # Mock db and binding check
    db = AsyncMock()
    
    mock_binding = MagicMock()
    db.execute.return_value.scalars.return_value.first.return_value = mock_binding
    
    # Mock client methods
    engine.client.get_default_models = AsyncMock(return_value={"default_chat_model": "test-model"})
    engine.client.search = AsyncMock(return_value=[{"id": "upstream-id-1"}])
    engine.client.ask_simple = AsyncMock(return_value={"answer": "Some answer"})
    
    # Mock citation mapper to return 0 mapped canonical sources
    with patch("app.integrations.open_notebook.ground_engine.map_citations", new_callable=AsyncMock) as mock_map:
        mock_map.return_value = ([], False) # No valid sources, not partial
        
        try:
            await engine.run(workspace_id=uuid4(), query="Hello", db=db)
            assert False, "Should have raised HTTPException 422"
        except HTTPException as e:
            assert e.status_code == 422
            assert "ground_provenance_failure: Zero mapped canonical evidence" in e.detail
