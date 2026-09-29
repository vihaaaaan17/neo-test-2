import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
from app.services.chat.context import resolve_ground_source_scope

@pytest.mark.asyncio
async def test_resolve_ground_source_scope_success():
    workspace_id = uuid4()
    s1 = uuid4()
    s2 = uuid4()

    session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [s1, s2]
    session.execute.return_value = mock_res

    resolved = await resolve_ground_source_scope(
        session=session,
        workspace_id=workspace_id,
        explicit_scope=[s1, s2]
    )
    assert set(resolved) == {s1, s2}

@pytest.mark.asyncio
async def test_resolve_ground_source_scope_fails_closed_on_foreign_or_missing_source():
    workspace_id = uuid4()
    valid_source = uuid4()
    foreign_source = uuid4()

    session = AsyncMock()
    mock_res = MagicMock()
    # Database only found valid_source in this workspace
    mock_res.scalars.return_value.all.return_value = [valid_source]
    session.execute.return_value = mock_res

    with pytest.raises(HTTPException) as exc_info:
        await resolve_ground_source_scope(
            session=session,
            workspace_id=workspace_id,
            explicit_scope=[valid_source, foreign_source]
        )
    assert exc_info.value.status_code == 400
    assert "Invalid source_scope" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_resolve_ground_source_scope_empty():
    workspace_id = uuid4()
    session = AsyncMock()
    resolved = await resolve_ground_source_scope(session, workspace_id, explicit_scope=None)
    assert resolved is None
