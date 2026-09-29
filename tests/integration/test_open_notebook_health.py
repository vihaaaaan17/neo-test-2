import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock, AsyncMock
from app.main import app

@pytest.fixture
def mock_health_deps():
    mock_engine = MagicMock()
    mock_conn = AsyncMock()
    mock_engine.connect.return_value.__aenter__.return_value = mock_conn
    return mock_engine

@pytest.mark.asyncio
async def test_health_check_open_notebook_disabled(monkeypatch, mock_health_deps):
    monkeypatch.setattr("app.core.config.settings.OPEN_NOTEBOOK_ENABLED", False)
    
    with patch("app.main.engine", mock_health_deps), patch("app.main.graph_store.execute_query", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["open_notebook"] == "disabled"

@pytest.mark.asyncio
async def test_health_check_open_notebook_enabled_healthy(monkeypatch, mock_health_deps):
    monkeypatch.setattr("app.core.config.settings.OPEN_NOTEBOOK_ENABLED", True)
    
    with patch("app.main.check_open_notebook_health", return_value=True), \
         patch("app.main.engine", mock_health_deps), patch("app.main.graph_store.execute_query", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["open_notebook"] == "ok"

@pytest.mark.asyncio
async def test_health_check_open_notebook_enabled_unhealthy(monkeypatch, mock_health_deps):
    monkeypatch.setattr("app.core.config.settings.OPEN_NOTEBOOK_ENABLED", True)
    
    with patch("app.main.check_open_notebook_health", return_value=False), \
         patch("app.main.engine", mock_health_deps), patch("app.main.graph_store.execute_query", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["open_notebook"] == "failed"
            assert data["status"] == "degraded"

