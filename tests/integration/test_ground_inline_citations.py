"""Open Notebook's inline `[source:<id>]` citations become canonical Ground evidence - for this workspace's sources only."""
import uuid

import pytest

from app.integrations.open_notebook.citation_mapper import map_citations
from app.integrations.open_notebook.ground_engine import inline_citation_ids
from app.models.open_notebook_binding import OpenNotebookSourceBinding
from app.models.source import Source, SourceSnapshot
from app.models.workspace import Workspace

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_inline_citations_map_to_this_workspaces_canonical_sources_only(db_session):
    ws, other_ws, owner = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    db_session.add_all([Workspace(workspace_id=ws, owner_id=owner), Workspace(workspace_id=other_ws, owner_id=owner)])
    await db_session.flush()
    mine, theirs = Source(workspace_id=ws, owner_id=owner), Source(workspace_id=other_ws, owner_id=owner)
    db_session.add_all([mine, theirs])
    await db_session.flush()
    snaps = [SourceSnapshot(source_id=s.source_id, file_uri="s3://x", filename="f.txt", size=1, checksum_sha256="0") for s in (mine, theirs)]
    db_session.add_all(snaps)
    await db_session.flush()
    on_mine, on_theirs = f"source:m{uuid.uuid4().hex[:12]}", f"source:t{uuid.uuid4().hex[:12]}"
    db_session.add_all([
        OpenNotebookSourceBinding(source_id=mine.source_id, snapshot_id=snaps[0].snapshot_id, checksum_sha256="0",
                                  open_notebook_source_id=on_mine, projection_status="ACTIVE"),
        OpenNotebookSourceBinding(source_id=theirs.source_id, snapshot_id=snaps[1].snapshot_id, checksum_sha256="0",
                                  open_notebook_source_id=on_theirs, projection_status="ACTIVE"),
    ])
    await db_session.commit()

    answer = f"Attention has no notion of order [{on_mine}]. Something else [{on_theirs}]."
    ids = inline_citation_ids(answer)
    assert ids == [on_mine, on_theirs]
    mapped, partial = await map_citations(ids, ws, db_session)
    assert mapped == [mine.source_id]  # the other workspace's source never becomes evidence here
    assert partial is True
