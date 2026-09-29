import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime, timezone

from app.models.scratchpad import ScratchpadEntry
from app.repositories.scratchpad import ScratchpadRepository
from app.schemas.scratchpad import (
    ScratchpadEntryCreate,
    ScratchpadEntryUpdate,
    ScratchpadEntryResponse,
    ScratchpadEntryListResponse
)


@pytest.mark.asyncio
async def test_scratchpad_repository_create_and_get():
    workspace_id = uuid4()
    conversation_id = uuid4()
    entry_id = uuid4()

    mock_entry = ScratchpadEntry(
        entry_id=entry_id,
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        entry_type="hypothesis",
        lifecycle="active",
        content="Nickel-based catalyst increases efficiency.",
        is_pinned_to_workspace=False,
        metadata_={"confidence": 0.85},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = mock_entry
    session.execute.return_value = mock_res

    repo = ScratchpadRepository(session)

    # Test get_entry
    fetched = await repo.get_entry(workspace_id, entry_id)
    assert fetched is not None
    assert fetched.entry_id == entry_id
    assert fetched.entry_type == "hypothesis"
    assert fetched.content == "Nickel-based catalyst increases efficiency."
    assert fetched.is_pinned_to_workspace is False


@pytest.mark.asyncio
async def test_scratchpad_repository_pinning_and_lifecycle():
    workspace_id = uuid4()
    entry_id = uuid4()

    mock_entry = ScratchpadEntry(
        entry_id=entry_id,
        workspace_id=workspace_id,
        entry_type="observation",
        lifecycle="active",
        content="Reaction temperature peaked at 350C.",
        is_pinned_to_workspace=False,
        metadata_={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = mock_entry
    session.execute.return_value = mock_res

    repo = ScratchpadRepository(session)

    # Pin to workspace
    pinned = await repo.pin_to_workspace(workspace_id, entry_id)
    assert pinned.is_pinned_to_workspace is True
    assert pinned.pinned_at is not None

    # Dismiss entry
    dismissed = await repo.set_lifecycle(workspace_id, entry_id, "dismissed")
    assert dismissed.lifecycle == "dismissed"

    # Unpin from workspace
    unpinned = await repo.unpin_from_workspace(workspace_id, entry_id)
    assert unpinned.is_pinned_to_workspace is False
    assert unpinned.pinned_at is None


@pytest.mark.asyncio
async def test_scratchpad_repository_supersede():
    workspace_id = uuid4()
    old_id = uuid4()
    new_id = uuid4()

    old_entry = ScratchpadEntry(
        entry_id=old_id,
        workspace_id=workspace_id,
        entry_type="hypothesis",
        lifecycle="active",
        content="Pt is the best catalyst.",
        metadata_={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = old_entry
    session.execute.return_value = mock_res

    repo = ScratchpadRepository(session)
    superseded = await repo.supersede_entry(workspace_id, old_id, new_id)
    assert superseded.lifecycle == "superseded"
    assert superseded.superseded_by_id == new_id


def test_scratchpad_schemas():
    """
    Test Pydantic v2 serialization and schema validation.
    """
    create_schema = ScratchpadEntryCreate(
        entry_type="finding",
        content="Found 3 matching papers on arXiv.",
        is_pinned_to_workspace=True,
        metadata={"count": 3}
    )
    assert create_schema.entry_type == "finding"
    assert create_schema.is_pinned_to_workspace is True

    now = datetime.now(timezone.utc)
    entry_id = uuid4()
    ws_id = uuid4()

    response_schema = ScratchpadEntryResponse(
        entry_id=entry_id,
        workspace_id=ws_id,
        entry_type="note",
        lifecycle="active",
        content="Review methodology in paper 2.",
        is_pinned_to_workspace=False,
        metadata={"priority": "high"},
        created_at=now,
        updated_at=now
    )
    dumped = response_schema.model_dump()
    assert dumped["entry_id"] == entry_id
    assert dumped["content"] == "Review methodology in paper 2."
    assert dumped["metadata"]["priority"] == "high"
