import pytest
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from app.models.knowledge import KnowledgeMemory
from app.models.research import ResearchEvidence
from app.models.scratchpad import ScratchpadEntry
from app.models.conversation import ConversationTurn
from app.services.chat.context import (
    build_research_context,
    estimate_tokens,
    sanitize_scratchpad_content,
    ResearchContext
)
from app.services.memory_router import MemoryRouter
from app.schemas.knowledge import KnowledgeMemoryCreate, Provenance


def test_estimate_tokens():
    assert estimate_tokens("") == 0
    assert estimate_tokens(None) == 0
    assert estimate_tokens("hi") == 1
    assert estimate_tokens("a" * 40) == 10


def test_sanitize_scratchpad_content():
    # Valid structured content
    valid = "Hypothesis: The reaction rate increases exponentially at 400K."
    assert sanitize_scratchpad_content(valid) == valid

    # Reject raw chain-of-thought markers
    assert sanitize_scratchpad_content("<thought>I should check the temperature</thought>") is None
    assert sanitize_scratchpad_content("Thinking Process: First let's review the data") is None
    assert sanitize_scratchpad_content("Internal reasoning: The user wants us to find X") is None
    assert sanitize_scratchpad_content("[cot] let us ponder") is None

    # Reject too short
    assert sanitize_scratchpad_content("abc") is None
    assert sanitize_scratchpad_content("") is None
    assert sanitize_scratchpad_content(None) is None


@pytest.mark.asyncio
async def test_build_research_context_aggregates_all_components():
    workspace_id = uuid4()
    conversation_id = uuid4()
    user_id = uuid4()
    now = datetime.now(timezone.utc)

    # 1. KnowledgeMemory record
    km = KnowledgeMemory(
        knowledge_id=uuid4(),
        workspace_id=workspace_id,
        owner_id=user_id,
        knowledge_type="fact",
        content="Accepted knowledge fact: Water boils at 100C.",
        status="accepted",
        provenance={"source_mode": "research"},
        created_at=now
    )

    # 2. ScratchpadEntry records
    sp1 = ScratchpadEntry(
        entry_id=uuid4(),
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        entry_type="hypothesis",
        lifecycle="active",
        content="Active hypothesis: pressure alters boiling point.",
        is_pinned_to_workspace=False,
        created_at=now - timedelta(minutes=5)
    )
    sp_pinned = ScratchpadEntry(
        entry_id=uuid4(),
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        entry_type="finding",
        lifecycle="active",
        content="Pinned finding: Atmospheric pressure at sea level is 1 atm.",
        is_pinned_to_workspace=True,
        pinned_at=now,
        created_at=now - timedelta(minutes=10)
    )

    # 3. Conversation Turn record
    turn1 = ConversationTurn(
        turn_id=uuid4(),
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        owner_id=user_id,
        sequence=1,
        mode="ground",
        user_message="What is the boiling point?",
        assistant_message="It is 100C at 1 atm.",
        status="completed"
    )

    # 4. Research Evidence record
    ev1 = ResearchEvidence(
        evidence_id=uuid4(),
        run_id=uuid4(),
        content="Evidence excerpt: Clausius-Clapeyron equation describes phase transitions.",
        retriever="arxiv",
        retrieved_at=now
    )

    # Output graph
    og = {"nodes": [{"id": "n1", "label": "Pressure"}], "edges": []}
    wm = {"active_hypotheses": ["Pressure varies with elevation"]}

    mock_session = AsyncMock()

    # Mock DB query results in order:
    # 1. km_stmt -> scalars().all() returns [km]
    # 2. turns_stmt -> scalars().all() returns [turn1]
    # 3. ev_stmt -> scalars().all() returns [ev1]
    km_result = MagicMock()
    km_result.scalars.return_value.all.return_value = [km]

    turns_result = MagicMock()
    turns_result.scalars.return_value.all.return_value = [turn1]

    ev_result = MagicMock()
    ev_result.scalars.return_value.all.return_value = [ev1]

    mock_session.execute = AsyncMock(side_effect=[km_result, turns_result, ev_result])

    with patch("app.services.chat.context.ScratchpadRepository") as mock_sp_repo_cls:
        mock_sp_repo = mock_sp_repo_cls.return_value
        mock_sp_repo.list_entries = AsyncMock(return_value=([sp1, sp_pinned], 2))

        ctx: ResearchContext = await build_research_context(
            session=mock_session,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            query="Analyze boiling thermodynamics",
            token_budget=10000,
            working_memory=wm,
            output_graph=og
        )

        assert ctx.workspace_id == workspace_id
        assert ctx.conversation_id == conversation_id
        assert ctx.query == "Analyze boiling thermodynamics"
        assert len(ctx.knowledge_memories) == 1
        assert len(ctx.scratchpad_entries) == 2
        assert len(ctx.turn_history) == 1
        assert len(ctx.research_evidence) == 1
        assert ctx.output_graph == og
        assert ctx.working_memory == wm
        assert len(ctx.context_version.evicted_items) == 0
        assert ctx.context_version.total_tokens > 0


@pytest.mark.asyncio
async def test_reverse_priority_eviction_order():
    """
    Eviction hierarchy order:
      1. Output Graph context (Dropped first)
      2. Older Research Evidence
      3. Distant conversation turns
      4. Older Scratchpad notes (unpinned before pinned)
      5. Accepted KnowledgeMemory
      6. Working Memory & Current Message (PRESERVED AT ALL COSTS)
    """
    workspace_id = uuid4()
    conversation_id = uuid4()
    user_id = uuid4()
    now = datetime.now(timezone.utc)

    # Create items with substantial length (~40 tokens each = 160 chars)
    km = KnowledgeMemory(
        knowledge_id=uuid4(),
        workspace_id=workspace_id,
        owner_id=user_id,
        knowledge_type="fact",
        content="K" * 160, # ~40 tokens
        status="accepted",
        created_at=now
    )

    sp_unpinned = ScratchpadEntry(
        entry_id=uuid4(),
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        entry_type="observation",
        lifecycle="active",
        content="S" * 160, # ~40 tokens
        is_pinned_to_workspace=False,
        created_at=now
    )

    turn = ConversationTurn(
        turn_id=uuid4(),
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        owner_id=user_id,
        sequence=1,
        mode="research",
        user_message="T" * 80,
        assistant_message="T" * 80, # ~40 tokens
        status="completed"
    )

    ev = ResearchEvidence(
        evidence_id=uuid4(),
        run_id=uuid4(),
        content="E" * 160, # ~40 tokens
        retriever="web",
        retrieved_at=now
    )

    og = {"data": "O" * 160} # ~40 tokens
    wm = {"notes": "W" * 160} # ~40 tokens
    query = "Q" * 160 # ~40 tokens

    # Total tokens is ~280 tokens.
    # If token_budget is 180:
    # Output Graph (rank 1) and Evidence (rank 2) should be evicted first!

    mock_session = AsyncMock()
    km_res = MagicMock()
    km_res.scalars.return_value.all.return_value = [km]
    turns_res = MagicMock()
    turns_res.scalars.return_value.all.return_value = [turn]
    ev_res = MagicMock()
    ev_res.scalars.return_value.all.return_value = [ev]
    mock_session.execute = AsyncMock(side_effect=[km_res, turns_res, ev_res])

    with patch("app.services.chat.context.ScratchpadRepository") as mock_sp_repo_cls:
        mock_sp_repo = mock_sp_repo_cls.return_value
        mock_sp_repo.list_entries = AsyncMock(return_value=([sp_unpinned], 1))

        # Budget allows ~180 tokens: og (~40 tokens) and ev (~40 tokens) must be evicted!
        ctx = await build_research_context(
            session=mock_session,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            query=query,
            token_budget=180,
            working_memory=wm,
            output_graph=og
        )

        evicted_types = [e.item_type for e in ctx.context_version.evicted_items]
        # Output graph must be the first evicted
        assert evicted_types[0] == "output_graph"
        # Evidence must be the next evicted
        assert "research_evidence" in evicted_types
        # Output graph is None in the assembled context
        assert ctx.output_graph is None
        # Working memory and current message are preserved
        assert ctx.working_memory == wm
        assert ctx.query == query


@pytest.mark.asyncio
async def test_working_memory_and_message_preserved_even_when_budget_exceeded():
    workspace_id = uuid4()
    conversation_id = uuid4()
    now = datetime.now(timezone.utc)

    query = "Current prompt " * 20 # ~70 tokens
    wm = {"active": "Important working hypothesis " * 10} # ~70 tokens

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))))

    with patch("app.services.chat.context.ScratchpadRepository") as mock_sp_repo_cls:
        mock_sp_repo = mock_sp_repo_cls.return_value
        mock_sp_repo.list_entries = AsyncMock(return_value=([], 0))

        # Budget is only 20 tokens, but current message & working memory MUST NOT be dropped!
        ctx = await build_research_context(
            session=mock_session,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            query=query,
            token_budget=20,
            working_memory=wm,
            output_graph=None
        )

        assert ctx.query == query
        assert ctx.working_memory == wm
        assert len(ctx.context_version.evicted_items) == 0
        assert ctx.context_version.total_tokens > 20


@pytest.mark.asyncio
async def test_memory_router_policy_enforcement():
    repo = AsyncMock()
    router = MemoryRouter(repository=repo)

    workspace_id = uuid4()
    owner_id = uuid4()

    # Ground mode is prohibited from writing KnowledgeMemory
    ground_mem = KnowledgeMemoryCreate(
        knowledge_type="finding",
        content="Ground answer",
        status="verified",
        provenance=Provenance(source_refs=[], source_mode="ground")
    )

    with pytest.raises(ValueError) as exc_info:
        await router.route_to_memory(owner_id, workspace_id, ground_mem)
    assert "Ground mode is strictly prohibited from writing KnowledgeMemory" in str(exc_info.value)
    repo.create_knowledge.assert_not_called()
