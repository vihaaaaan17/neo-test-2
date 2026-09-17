import pytest
import asyncio
from uuid import uuid4
from fastapi import HTTPException
from unittest.mock import AsyncMock, MagicMock

from app.services.quota import QuotaService
from app.core.config import settings

@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.execute.return_value = MagicMock()
    return db

@pytest.mark.asyncio
async def test_check_workspace_limit_pass(mock_db):
    # Setup mock to return count less than limit
    mock_db.execute.return_value.scalar.return_value = settings.MAX_WORKSPACES_PER_USER - 1
    
    quota_service = QuotaService(mock_db)
    # Should not raise exception
    await quota_service.check_workspace_limit(uuid4())

@pytest.mark.asyncio
async def test_check_workspace_limit_fail(mock_db):
    # Setup mock to return count equal to limit
    mock_db.execute.return_value.scalar.return_value = settings.MAX_WORKSPACES_PER_USER
    
    quota_service = QuotaService(mock_db)
    with pytest.raises(HTTPException) as excinfo:
        await quota_service.check_workspace_limit(uuid4())
    
    assert excinfo.value.status_code == 403
    assert "Quota exceeded" in excinfo.value.detail

@pytest.mark.asyncio
async def test_check_source_limit_fail(mock_db):
    mock_db.execute.return_value.scalar.return_value = settings.MAX_SOURCES_PER_WORKSPACE
    
    quota_service = QuotaService(mock_db)
    with pytest.raises(HTTPException) as excinfo:
        await quota_service.check_source_limit(uuid4())
    
    assert excinfo.value.status_code == 403

@pytest.mark.asyncio
async def test_check_storage_limit_fail(mock_db):
    # Currently 499MB used
    mock_db.execute.return_value.scalar.return_value = settings.MAX_STORAGE_BYTES_PER_WORKSPACE - 1_000_000
    
    quota_service = QuotaService(mock_db)
    # Trying to upload 2MB -> exceeds 500MB
    with pytest.raises(HTTPException) as excinfo:
        await quota_service.check_storage_limit(uuid4(), 2_000_000)
    
    assert excinfo.value.status_code == 403

@pytest.mark.asyncio
async def test_check_knowledge_limit_fail(mock_db):
    mock_db.execute.return_value.scalar.return_value = settings.MAX_KNOWLEDGE_PER_WORKSPACE
    
    quota_service = QuotaService(mock_db)
    with pytest.raises(HTTPException) as excinfo:
        await quota_service.check_knowledge_limit(uuid4())
    
    assert excinfo.value.status_code == 403
