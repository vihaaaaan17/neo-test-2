import httpx
import logging
from typing import Any
from functools import wraps
from fastapi import HTTPException
from app.integrations.open_notebook.config import get_open_notebook_base_url, get_open_notebook_timeout

import uuid
import time
import threading
from enum import Enum
from opentelemetry import propagate, trace

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = 1
    OPEN = 2
    HALF_OPEN = 3

class CircuitBreaker:
    def __init__(self, failure_threshold=3, recovery_timeout=30.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.last_failure_time = 0.0
        self._lock = threading.Lock()
        
    def record_failure(self):
        with self._lock:
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                self.last_failure_time = time.time()
                
    def record_success(self):
        with self._lock:
            self.failure_count = 0
            self.state = CircuitState.CLOSED
            
    def check_state(self):
        with self._lock:
            if self.state == CircuitState.OPEN:
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    return True # Allow trial
                return False
            return True

circuit_breaker = CircuitBreaker()

def with_error_translation(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if not circuit_breaker.check_state():
            raise HTTPException(status_code=503, detail="ground_dependency_unavailable")
            
        try:
            result = await func(*args, **kwargs)
            circuit_breaker.record_success()
            return result
        except httpx.HTTPStatusError as e:
            if e.response.status_code >= 500:
                circuit_breaker.record_failure()
            logger.error(f"Open Notebook HTTPStatusError: {e.response.status_code} - {e.response.text}")
            
            # Map 404 for session endpoints to 409
            if e.response.status_code == 404 and "session" in str(e.request.url):
                raise HTTPException(status_code=409, detail="session_state_lost")
                
            if e.response.status_code in [400, 422]:
                raise HTTPException(status_code=400, detail="ground_validation_error")
            elif e.response.status_code >= 500:
                raise HTTPException(status_code=502, detail="ground_execution_failed")
            # For 401, 403, 404, etc. map generally unless overridden
            raise HTTPException(status_code=502, detail="ground_execution_failed")
        except httpx.RequestError as e:
            circuit_breaker.record_failure()
            logger.error(f"Open Notebook RequestError: {str(e)}")
            raise HTTPException(status_code=503, detail="ground_dependency_unavailable")
    return wrapper

class OpenNotebookClient:
    """
    HTTP client for communicating with the Open Notebook API.
    
    Establishes the integration boundary and handles basic transport.
    """
    
    def __init__(self, workspace_id: str = None, http_client: httpx.AsyncClient = None):
        self.base_url = get_open_notebook_base_url()
        self.timeout = get_open_notebook_timeout()
        self.workspace_id = workspace_id
        self.http_client = http_client
        
    from contextlib import asynccontextmanager
    @asynccontextmanager
    async def _get_client(self, custom_timeout: float = None):
        if self.http_client:
            yield self.http_client
        else:
            limits = httpx.Limits(max_connections=50, max_keepalive_connections=20)
            async with httpx.AsyncClient(timeout=custom_timeout or self.timeout, limits=limits) as client:
                yield client
        
    def _get_headers(self) -> dict[str, str]:
        headers = {}
        
        # Inject standard correlation headers
        from app.core.telemetry import neosis_run_id, neosis_task_id, neosis_request_id
        current_run_id = neosis_run_id.get()
        headers["X-Neosis-Run-ID"] = current_run_id if current_run_id else str(uuid.uuid4())
        
        current_task_id = neosis_task_id.get()
        if current_task_id:
            headers["X-Neosis-Task-ID"] = current_task_id
            
        current_request_id = neosis_request_id.get()
        
        # Use OTEL trace id if available, else fallback to contextvar or new UUID
        span = trace.get_current_span()
        if span.is_recording():
            trace_id = span.get_span_context().trace_id
            headers["X-Neosis-Request-ID"] = f"{trace_id:032x}"
        else:
            headers["X-Neosis-Request-ID"] = current_request_id if current_request_id else str(uuid.uuid4())
            
        if self.workspace_id:
            headers["X-Neosis-Workspace-ID"] = str(self.workspace_id)
            
        # Standard OpenTelemetry propagation
        propagate.inject(headers)
        return headers
        
    @with_error_translation
    async def get_health(self) -> dict[str, Any]:
        """
        Check health endpoint of Open Notebook.
        Returns the parsed JSON response.
        Raises httpx.HTTPError on failure.
        """
        async with self._get_client() as client:
            response = await client.get(f"{self.base_url}/health", headers=self._get_headers())
            response.raise_for_status()
            return response.json()

    @with_error_translation
    async def create_notebook(self, title: str) -> str:
        async with self._get_client() as client:
            response = await client.post(
                f"{self.base_url}/api/notebooks", 
                json={"name": title},
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json().get("id")

    @with_error_translation
    async def upload_source(self, notebook_id: str, file_path: str, title: str) -> str:
        import json
        import mimetypes
        import os
        
        notebooks_json = json.dumps([notebook_id])
        data = {
            "type": "file",
            "notebooks": notebooks_json,
            "title": title
        }
        
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = "application/octet-stream"
            
        filename = os.path.basename(file_path)
        
        async with self._get_client(custom_timeout=120.0) as client:
            with open(file_path, "rb") as f:
                files = {"file": (filename, f, mime_type)}
                response = await client.post(
                    f"{self.base_url}/api/sources",
                    data=data,
                    files=files,
                    headers=self._get_headers()
                )
                response.raise_for_status()
                return response.json().get("id")

    @with_error_translation
    async def delete_source(self, source_id: str) -> None:
        async with self._get_client() as client:
            response = await client.delete(f"{self.base_url}/api/sources/{source_id}", headers=self._get_headers())
            # Ignore 404 if already deleted
            if response.status_code != 404:
                response.raise_for_status()

    @with_error_translation
    async def delete_notebook(self, notebook_id: str, delete_exclusive_sources: bool = True) -> None:
        async with self._get_client() as client:
            flag = str(delete_exclusive_sources).lower()
            response = await client.delete(
                f"{self.base_url}/api/notebooks/{notebook_id}?delete_exclusive_sources={flag}",
                headers=self._get_headers()
            )
            if response.status_code != 404:
                response.raise_for_status()

    @with_error_translation
    async def get_default_models(self) -> dict[str, Any]:
        async with self._get_client() as client:
            response = await client.get(f"{self.base_url}/api/models/default", headers=self._get_headers())
            response.raise_for_status()
            return response.json()

    @with_error_translation
    async def search(self, query: str, limit: int = 100) -> list[dict[str, Any]]:
        async with self._get_client() as client:
            response = await client.post(
                f"{self.base_url}/api/search",
                json={
                    "query": query,
                    "type": "text",
                    "limit": limit,
                    "search_sources": True,
                    "search_notes": False,
                    "minimum_score": 0.2
                },
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json().get("results", [])

    @with_error_translation
    async def ask_simple(
        self, 
        question: str, 
        strategy_model: str, 
        answer_model: str, 
        final_answer_model: str
    ) -> dict[str, Any]:
        async with self._get_client(custom_timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/api/search/ask/simple",
                json={
                    "question": question,
                    "strategy_model": strategy_model,
                    "answer_model": answer_model,
                    "final_answer_model": final_answer_model
                },
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()

    async def ask_stream(
        self, 
        question: str, 
        strategy_model: str, 
        answer_model: str, 
        final_answer_model: str
    ):
        """Streams the ask response, yielding standardized SSE events."""
        if not circuit_breaker.check_state():
            yield "event: error\ndata: {\"message\": \"ground_dependency_unavailable\"}\n\n"
            return
            
        try:
            async with self._get_client(custom_timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/search/ask",
                    json={
                        "question": question,
                        "strategy_model": strategy_model,
                        "answer_model": answer_model,
                        "final_answer_model": final_answer_model
                    },
                    headers=self._get_headers()
                ) as response:
                    if response.status_code == 404 and "session" in str(response.request.url):
                        yield "event: error\ndata: {\"message\": \"session_state_lost\"}\n\n"
                        return
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            try:
                                import json
                                payload = json.loads(line[6:])
                                ev_type = payload.get("type")
                                
                                # Remap ON tokens to standard Neosis events
                                if ev_type == "strategy":
                                    yield f"event: strategy\ndata: {json.dumps({'reasoning': payload.get('reasoning'), 'searches': payload.get('searches')})}\n\n"
                                elif ev_type == "answer":
                                    yield f"event: answer\ndata: {json.dumps({'content': payload.get('content')})}\n\n"
                                elif ev_type == "final_answer":
                                    yield f"event: final_answer\ndata: {json.dumps({'content': payload.get('content')})}\n\n"
                                elif ev_type == "complete":
                                    yield f"event: complete\ndata: {json.dumps({'final_answer': payload.get('final_answer')})}\n\n"
                                elif ev_type == "error":
                                    yield f"event: error\ndata: {json.dumps({'message': payload.get('message')})}\n\n"
                            except Exception as e:
                                logger.error(f"Error parsing Open Notebook stream event: {e}")
        except Exception as e:
            logger.error(f"Error communicating with Open Notebook stream: {e}")
            circuit_breaker.record_failure()
            yield f"event: error\ndata: {{\"message\": \"ground_dependency_unavailable\"}}\n\n"

    @with_error_translation
    async def create_chat_session(self, notebook_id: str) -> str:
        async with self._get_client() as client:
            response = await client.post(
                f"{self.base_url}/api/chat/sessions",
                json={"notebook_id": notebook_id},
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json().get("id")

    async def chat_execute(self, session_id: str, notebook_id: str, message: str) -> dict[str, Any]:
        """
        Executes a chat message. Returns the final answer text and the updated messages.
        Note: We manually handle HTTP errors here to specifically trap 404s for missing sessions.
        """
        if not circuit_breaker.check_state():
            raise HTTPException(status_code=503, detail="ground_dependency_unavailable")
            
        async with self._get_client(custom_timeout=120.0) as client:
            # First, build context for this notebook
            try:
                context_res = await client.post(
                    f"{self.base_url}/api/chat/context",
                    json={"notebook_id": notebook_id, "context_config": {}},
                    headers=self._get_headers()
                )
                context_res.raise_for_status()
                context_data = context_res.json().get("context", {})
                
                # Execute the chat message
                exec_res = await client.post(
                    f"{self.base_url}/api/chat/execute",
                    json={
                        "session_id": session_id,
                        "message": message,
                        "context": context_data
                    },
                    headers=self._get_headers()
                )
                exec_res.raise_for_status()
                
                circuit_breaker.record_success()
                
                result = exec_res.json()
                
                # Extract the last AI message
                messages = result.get("messages", [])
                answer = ""
                for msg in reversed(messages):
                    if msg.get("type") == "ai":
                        answer = msg.get("content", "")
                        break
                        
                return {
                    "answer": answer,
                    "messages": messages
                }
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500:
                    circuit_breaker.record_failure()
                logger.error(f"Open Notebook chat HTTPStatusError: {e.response.status_code} - {e.response.text}")
                if e.response.status_code == 404:
                    raise HTTPException(status_code=400, detail="conversation_session_expired")
                elif e.response.status_code in [400, 422]:
                    raise HTTPException(status_code=400, detail="ground_validation_error")
                elif e.response.status_code >= 500:
                    raise HTTPException(status_code=502, detail="ground_execution_failed")
                raise HTTPException(status_code=502, detail="ground_execution_failed")
            except httpx.RequestError as e:
                circuit_breaker.record_failure()
                logger.error(f"Open Notebook chat RequestError: {str(e)}")
                raise HTTPException(status_code=503, detail="ground_dependency_unavailable")
