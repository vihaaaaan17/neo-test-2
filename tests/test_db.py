"""
Integration tests for the database layer.

These require a live Postgres instance. They are automatically skipped when
Postgres is not reachable. Run with:  docker-compose up -d && pytest -m integration
"""
import pytest
import uuid
from sqlalchemy import text
from app.core.database import engine, async_session_maker
from app.models.workspace import Workspace


@pytest.mark.asyncio
@pytest.mark.integration
async def test_db_connection():
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar() == 1


@pytest.mark.asyncio
@pytest.mark.integration
async def test_create_workspace():
    # Note: creates tables for the test
    async with engine.begin() as conn:
        await conn.run_sync(Workspace.metadata.create_all)

    async with async_session_maker() as session:
        new_ws = Workspace(owner_id=uuid.uuid4())
        session.add(new_ws)
        await session.commit()
        await session.refresh(new_ws)

        assert new_ws.workspace_id is not None
        assert new_ws.status == "active"
