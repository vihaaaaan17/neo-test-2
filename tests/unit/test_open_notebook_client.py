import pytest
import httpx
from unittest.mock import patch, MagicMock, AsyncMock
from app.integrations.open_notebook.client import OpenNotebookClient, circuit_breaker, CircuitState
from fastapi import HTTPException
import uuid

pytestmark = pytest.mark.asyncio

@pytest.fixture(autouse=True)
def reset_circuit_breaker():
    # Reset circuit breaker before each test
    with circuit_breaker._lock:
        circuit_breaker.state = CircuitState.CLOSED
        circuit_breaker.failure_count = 0
        circuit_breaker.last_failure_time = 0.0

async def test_circuit_breaker_trips_on_failures():
    client = OpenNotebookClient()
    
    with patch("httpx.AsyncClient.get") as mock_get:
        # Simulate 503 response
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.text = "Service Unavailable"
        
        # Raise HTTPStatusError
        error = httpx.HTTPStatusError("503 Server Error", request=MagicMock(), response=mock_response)
        mock_get.side_effect = error
        
        # 1st failure
        with pytest.raises(HTTPException) as exc:
            await client.get_health()
        assert exc.value.status_code == 502
        assert circuit_breaker.state == CircuitState.CLOSED
        
        # 2nd failure
        with pytest.raises(HTTPException):
            await client.get_health()
        assert circuit_breaker.state == CircuitState.CLOSED
        
        # 3rd failure - should trip the breaker
        with pytest.raises(HTTPException):
            await client.get_health()
        assert circuit_breaker.state == CircuitState.OPEN
        
        # 4th call - should immediately raise 503 without calling the mock
        mock_get.reset_mock()
        with pytest.raises(HTTPException) as exc:
            await client.get_health()
        assert exc.value.status_code == 503
        assert exc.value.detail == "ground_dependency_unavailable"
        mock_get.assert_not_called()

async def test_circuit_breaker_trips_on_timeouts():
    client = OpenNotebookClient()
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.side_effect = httpx.RequestError("Timeout")
        
        for _ in range(3):
            with pytest.raises(HTTPException) as exc:
                await client.get_health()
            assert exc.value.status_code == 503
            
        assert circuit_breaker.state == CircuitState.OPEN
        
        # Next call fails fast
        mock_get.reset_mock()
        with pytest.raises(HTTPException) as exc:
            await client.get_health()
        assert exc.value.status_code == 503
        mock_get.assert_not_called()

async def test_telemetry_headers_injected():
    workspace_id = str(uuid.uuid4())
    client = OpenNotebookClient(workspace_id=workspace_id)
    
    from app.core.telemetry import neosis_run_id, neosis_task_id, neosis_request_id
    
    # Set context vars
    run_id = "test-run-123"
    task_id = "test-task-456"
    request_id = "test-req-789"
    
    token_run = neosis_run_id.set(run_id)
    token_task = neosis_task_id.set(task_id)
    token_req = neosis_request_id.set(request_id)
    
    try:
        with patch("httpx.AsyncClient.post") as mock_post:
            # Mock success
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"id": "notebook:123"}
            mock_post.return_value = mock_response
            
            await client.create_notebook("Test Notebook")
            
            # Verify headers were passed
            assert mock_post.called
            kwargs = mock_post.call_args.kwargs
            assert "headers" in kwargs
            headers = kwargs["headers"]
            
            assert headers.get("X-Neosis-Run-ID") == run_id
            assert headers.get("X-Neosis-Task-ID") == task_id
            assert headers.get("X-Neosis-Request-ID") == request_id
            assert headers.get("X-Neosis-Workspace-ID") == workspace_id
    finally:
        neosis_run_id.reset(token_run)
        neosis_task_id.reset(token_task)
        neosis_request_id.reset(token_req)

async def test_ask_stream_yields_neosis_sse():
    client = OpenNotebookClient()
    
    # Mock AsyncClient.stream context manager
    mock_response = AsyncMock()
    mock_response.raise_for_status = MagicMock()
    
    # Mock aiter_lines to yield Open Notebook events
    async def mock_aiter_lines():
        yield 'data: {"type": "strategy", "reasoning": "thinking...", "searches": []}'
        yield 'data: {"type": "answer", "content": "hello"}'
        yield 'data: {"type": "final_answer", "content": "hello world"}'
        yield 'data: {"type": "complete", "final_answer": "hello world"}'
        
    mock_response.aiter_lines = mock_aiter_lines
    
    mock_stream_cm = AsyncMock()
    mock_stream_cm.__aenter__.return_value = mock_response
    
    with patch("httpx.AsyncClient.stream", return_value=mock_stream_cm):
        events = []
        async for ev in client.ask_stream("hi", "strat", "ans", "final"):
            events.append(ev)
            
        assert len(events) == 4
        assert events[0].startswith("event: strategy\ndata: ")
        assert events[1] == 'event: answer\ndata: {"content": "hello"}\n\n'
        assert events[2] == 'event: final_answer\ndata: {"content": "hello world"}\n\n'
        assert events[3] == 'event: complete\ndata: {"final_answer": "hello world"}\n\n'
