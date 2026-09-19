import pytest
from httpx import AsyncClient
from unittest.mock import patch
from app.main import app

@pytest.mark.asyncio
async def test_health_check_open_notebook_disabled(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.OPEN_NOTEBOOK_ENABLED", False)
    
    # We mock the internal graph/db checks so they don't fail the test
    with patch("app.main.engine.connect"), patch("app.main.graph_store.execute_query"):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["open_notebook"] == "disabled"

@pytest.mark.asyncio
async def test_health_check_open_notebook_enabled_healthy(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.OPEN_NOTEBOOK_ENABLED", True)
    
    with patch("app.main.check_open_notebook_health", return_value=True), \
         patch("app.main.engine.connect"), patch("app.main.graph_store.execute_query"):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["open_notebook"] == "ok"

@pytest.mark.asyncio
async def test_health_check_open_notebook_enabled_unhealthy(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.OPEN_NOTEBOOK_ENABLED", True)
    
    with patch("app.main.check_open_notebook_health", return_value=False), \
         patch("app.main.engine.connect"), patch("app.main.graph_store.execute_query"):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["open_notebook"] == "failed"
            assert data["status"] == "degraded"
