import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID
from datetime import datetime, timezone

from app.models.workspace import Workspace, WorkspaceCommit
from app.models.scratchpad import ScratchpadEntry
from app.models.knowledge import KnowledgeMemory
from app.models.research import ResearchRun, ResearchEvidence
from app.models.conversation import Conversation, ConversationTurn
from app.repositories.workspace import WorkspaceRepository
from app.repositories.scratchpad import ScratchpadRepository, ScratchpadWorkspaceMismatchError
from app.services.chat.context import build_research_context
from app.schemas.workspace import ResearchRequest
from app.schemas.ground_mode import AskRequest
from app.api.routes.workspaces import start_research, ask_ground_mode, ask_ground_mode_stream


@pytest.mark.asyncio
async def test_commit_creation_atomicity_and_manifest():
    """Gate 1: create_commit_with_manifest captures complete state and updates active_commit_id atomically."""
    workspace_id = uuid4()
    parent_id = uuid4()
    k1 = uuid4()
    k2 = uuid4()
    sp1 = uuid4()

    mock_workspace = Workspace(
        workspace_id=workspace_id,
        owner_id=uuid4(),
        status="active",
        timeline_epoch=2,
        active_commit_id=parent_id
    )

    session = AsyncMock()
    # Mock workspace lookup and scratchpad lookup
    ws_res = MagicMock()
    ws_res.scalars.return_value.first.return_value = mock_workspace

    sp_res = MagicMock()
    sp_res.scalars.return_value.all.return_value = [sp1]

    def mock_execute(stmt):
        # Check statement table
        sql_str = str(stmt).lower()
        res = MagicMock()
        if "scratchpad" in sql_str:
            res.scalars.return_value.all.return_value = [sp1]
        else:
            res.scalars.return_value.first.return_value = mock_workspace
        return res

    session.execute = AsyncMock(side_effect=mock_execute)
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    repo = WorkspaceRepository(session)
    commit = await repo.create_commit_with_manifest(
        workspace_id=workspace_id,
        parent_id=parent_id,
        active_knowledge_ids=[k1, k2],
        manifest=None  # Should auto-capture knowledge, scratchpad, and graph
    )

    assert commit.workspace_id == workspace_id
    assert commit.parent_id == parent_id
    assert commit.active_knowledge_ids == [str(k1), str(k2)]

    # Manifest checks
    manifest = commit.manifest
    assert manifest["knowledge_memory_ids"] == [str(k1), str(k2)]
    assert manifest["scratchpad_ids"] == [str(sp1)]
    assert "output_graph_version" in manifest
    assert "graph_references" in manifest

    # Atomicity: workspace.active_commit_id must be updated to commit.commit_id
    assert mock_workspace.active_commit_id == commit.commit_id
    assert session.flush.called
    assert session.commit.called


@pytest.mark.asyncio
async def test_build_research_context_rollback_aware():
    """Gate 2: build_research_context filters to entities in active commit manifest, hiding post-rollback data."""
    workspace_id = uuid4()
    conversation_id = uuid4()
    active_commit_id = uuid4()

    km_active_id = uuid4()
    km_stale_id = uuid4()

    sp_active_id = uuid4()
    sp_stale_id = uuid4()

    mock_workspace = Workspace(
        workspace_id=workspace_id,
        owner_id=uuid4(),
        status="active",
        active_commit_id=active_commit_id,
        timeline_epoch=3
    )

    # Manifest only includes km_active_id and sp_active_id (km_stale_id was added after this commit)
    mock_commit = WorkspaceCommit(
        commit_id=active_commit_id,
        workspace_id=workspace_id,
        parent_id=None,
        active_knowledge_ids=[str(km_active_id)],
        manifest={
            "knowledge_memory_ids": [str(km_active_id)],
            "scratchpad_ids": [str(sp_active_id)]
        }
    )

    km_active = KnowledgeMemory(
        knowledge_id=km_active_id,
        workspace_id=workspace_id,
        content="Active verified knowledge",
        knowledge_type="fact",
        status="accepted",
        created_at=datetime.now(timezone.utc)
    )
    km_stale = KnowledgeMemory(
        knowledge_id=km_stale_id,
        workspace_id=workspace_id,
        content="Post-rollback knowledge that must be excluded",
        knowledge_type="fact",
        status="accepted",
        created_at=datetime.now(timezone.utc)
    )

    sp_active = ScratchpadEntry(
        entry_id=sp_active_id,
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        entry_type="note",
        lifecycle="active",
        content="Active scratchpad note",
        is_pinned_to_workspace=False,
        created_at=datetime.now(timezone.utc)
    )
    sp_stale = ScratchpadEntry(
        entry_id=sp_stale_id,
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        entry_type="note",
        lifecycle="active",
        content="Stale scratchpad note that must be excluded",
        is_pinned_to_workspace=False,
        created_at=datetime.now(timezone.utc)
    )

    session = AsyncMock()

    def mock_execute(stmt):
        sql_str = str(stmt).lower()
        res = MagicMock()
        if "workspace_commits" in sql_str:
            res.scalars.return_value.first.return_value = mock_commit
        elif "workspaces" in sql_str:
            res.scalars.return_value.first.return_value = mock_workspace
        elif "knowledge_memories" in sql_str:
            # If query had knowledge_id.in_([km_active_id]), return only active
            # simulate DB filtering
            res.scalars.return_value.all.return_value = [km_active]
        elif "scratchpad" in sql_str:
            res.scalars.return_value.all.return_value = [sp_active, sp_stale]
            res.scalar_one.return_value = 2
        else:
            res.scalars.return_value.all.return_value = []
            res.scalars.return_value.first.return_value = None
        return res

    session.execute = AsyncMock(side_effect=mock_execute)

    with patch("app.services.chat.context.ScratchpadRepository.list_entries",
               new_callable=AsyncMock, return_value=([sp_active, sp_stale], 2)):
        ctx = await build_research_context(
            session=session,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            query="test query",
            token_budget=4000
        )

    included_ids = [item.item_id for item in ctx.context_version.included_items]

    # km_active should be included, km_stale excluded
    assert str(km_active_id) in included_ids
    assert str(km_stale_id) not in included_ids

    # sp_active should be included, sp_stale excluded
    assert str(sp_active_id) in included_ids
    assert str(sp_stale_id) not in included_ids


@pytest.mark.asyncio
async def test_scratchpad_repository_cross_linked_id_fail_closed():
    """Gate 3: Scratchpad mutations fail closed when referenced IDs belong to another workspace."""
    workspace_id = uuid4()
    other_workspace_id = uuid4()
    conv_id = uuid4()
    run_id = uuid4()
    ev_id = uuid4()

    session = AsyncMock()

    # 1. Foreign conversation_id check
    def mock_execute_conv(stmt):
        res = MagicMock()
        res.scalar_one_or_none.return_value = other_workspace_id  # Mismatched!
        return res

    session.execute = AsyncMock(side_effect=mock_execute_conv)
    repo = ScratchpadRepository(session)

    with pytest.raises(ScratchpadWorkspaceMismatchError, match="conversation_id"):
        await repo.create_entry(
            workspace_id=workspace_id,
            entry_type="note",
            content="test content",
            conversation_id=conv_id
        )

    # 2. Foreign run_id check
    def mock_execute_run(stmt):
        res = MagicMock()
        res.scalar_one_or_none.return_value = other_workspace_id  # Mismatched!
        return res

    session.execute = AsyncMock(side_effect=mock_execute_run)
    with pytest.raises(ScratchpadWorkspaceMismatchError, match="run_id"):
        await repo.create_entry(
            workspace_id=workspace_id,
            entry_type="hypothesis",
            content="test content",
            run_id=run_id
        )

    # 3. Foreign evidence_id check in metadata
    def mock_execute_ev(stmt):
        res = MagicMock()
        res.scalar_one_or_none.return_value = other_workspace_id  # Mismatched!
        return res

    session.execute = AsyncMock(side_effect=mock_execute_ev)
    with pytest.raises(ScratchpadWorkspaceMismatchError, match="evidence_id"):
        await repo.create_entry(
            workspace_id=workspace_id,
            entry_type="observation",
            content="test content",
            metadata={"evidence_ids": [str(ev_id)]}
        )

    # 4. update_entry with foreign evidence_id
    existing_entry = ScratchpadEntry(
        entry_id=uuid4(),
        workspace_id=workspace_id,
        entry_type="note",
        lifecycle="active",
        content="old content"
    )
    mock_get = MagicMock()
    mock_get.scalars.return_value.first.return_value = existing_entry
    session.execute = AsyncMock(side_effect=[mock_get, mock_execute_ev(None)])

    with pytest.raises(ScratchpadWorkspaceMismatchError):
        await repo.update_entry(
            workspace_id=workspace_id,
            entry_id=existing_entry.entry_id,
            metadata={"evidence_ids": [str(ev_id)]}
        )

    # 5. supersede_entry with new_entry belonging to another workspace (get_entry returns None)
    mock_get_old = MagicMock()
    mock_get_old.scalars.return_value.first.return_value = existing_entry
    mock_get_new = MagicMock()
    mock_get_new.scalars.return_value.first.return_value = None  # Not found in workspace

    session.execute = AsyncMock(side_effect=[mock_get_old, mock_get_new])
    with pytest.raises(ScratchpadWorkspaceMismatchError, match="new_entry_id"):
        await repo.supersede_entry(
            workspace_id=workspace_id,
            old_entry_id=existing_entry.entry_id,
            new_entry_id=uuid4()
        )


@pytest.mark.asyncio
async def test_legacy_routes_delegate_to_chatservice():
    """Gate 4: Legacy endpoints delegate strictly via ChatService without unmonitored state or bypasses."""
    workspace_id = uuid4()
    user_id = uuid4()
    conv_id = uuid4()
    turn_id = uuid4()

    mock_workspace = Workspace(
        workspace_id=workspace_id,
        owner_id=user_id,
        status="active"
    )

    mock_conv = Conversation(
        conversation_id=conv_id,
        workspace_id=workspace_id,
        owner_id=user_id,
        title="Existing active conversation",
        status="active"
    )

    mock_turn = ConversationTurn(
        turn_id=turn_id,
        conversation_id=conv_id,
        workspace_id=workspace_id,
        owner_id=user_id,
        sequence=1,
        mode="research",
        user_message="research query",
        assistant_message="research report",
        status="completed",
        research_run_id=uuid4()
    )

    repo = AsyncMock()
    repo.get_workspace.return_value = mock_workspace

    db = AsyncMock()
    research_repo = AsyncMock()
    arq_redis = AsyncMock()

    # 1. start_research delegates strictly to ChatService.submit_turn
    with patch("app.api.routes.workspaces.ConversationRepository.list_conversations",
               new_callable=AsyncMock, return_value=([mock_conv], 1)), \
         patch("app.api.routes.workspaces.ChatService.submit_turn",
               new_callable=AsyncMock, return_value=mock_turn) as mock_submit:

        resp = await start_research(
            workspace_id=workspace_id,
            request=ResearchRequest(objective="Quantum gravity research"),
            current_user_id=user_id,
            repo=repo,
            research_repo=research_repo,
            db=db,
            arq_redis=arq_redis
        )

        assert mock_submit.called
        call_kwargs = mock_submit.call_args.kwargs
        assert call_kwargs["workspace_id"] == workspace_id
        assert call_kwargs["conversation_id"] == conv_id
        assert call_kwargs["turn_create"].mode == "research"
        assert resp["status"] == "accepted"
        assert resp["turn_id"] == str(turn_id)

    # 2. ask_ground_mode delegates strictly to ChatService.submit_turn and reuses conversation
    ground_engine = AsyncMock()
    with patch("app.api.routes.workspaces.ConversationRepository.list_conversations",
               new_callable=AsyncMock, return_value=([mock_conv], 1)), \
         patch("app.api.routes.workspaces.ConversationRepository.list_events_after",
               new_callable=AsyncMock, return_value=[]), \
         patch("app.api.routes.workspaces.ChatService.submit_turn",
               new_callable=AsyncMock, return_value=mock_turn) as mock_ask_submit:

        response_obj = MagicMock()
        ask_resp = await ask_ground_mode(
            workspace_id=workspace_id,
            request=AskRequest(query="What is quantum gravity?"),
            response=response_obj,
            current_user_id=user_id,
            repo=repo,
            db=db,
            ground_engine=ground_engine,
            arq_redis=arq_redis
        )

        assert mock_ask_submit.called
        assert mock_ask_submit.call_args.kwargs["conversation_id"] == conv_id
        assert ask_resp.conversation_id == conv_id
