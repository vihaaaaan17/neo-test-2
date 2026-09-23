"""
Shared HTTP client for Open Notebook integration.
"""
import httpx
from app.core.config import settings

# Shared HTTP client for Open Notebook
shared_http_client = httpx.AsyncClient(
    base_url=settings.OPEN_NOTEBOOK_BASE_URL,
    limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    timeout=30.0
)