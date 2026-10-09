"""
ODR adapter contract (Chapter 5, Phase 1):
  * the adapter formats/prepends context and yields progress + exactly one `final_report` event;
  * it never persists reports/candidates and never yields terminal statuses (failures are raised);
  * persistence of the report + pending_review memory_candidate lives in ResearchService.finalize_report;
  * the worker resolves context/evidence and forwards them as plain data.
"""
import asyncio
import inspect
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integrations.research_engine.open_deep_research.engine import OpenDeepResearchEngine
from app.services.research.context import build_prior_evidence_context, format_research_context
from app.services.research.service import ResearchService


# --------------------------------------------------------------------------- #
# format_research_context / build_prior_evidence_context (engine-agnostic)
# --------------------------------------------------------------------------- #

def test_format_research_context_full():
    """All canonical context sections are formatted into an authoritative block."""
    workspace_id = uuid4()
    conversation_id = uuid4()

    context_dict = {
        "workspace_id": str(workspace_id),
        "conversation_id": str(conversation_id),
        "query": "Investigate ambient superconductor mechanisms",
        "context_version": {"version": "v1", "budget": 8000, "total_tokens": 1250},
        "working_memory": {
            "focus": "cuprate perovksites",
            "active_hypothesis": "H1: phonon coupling enhancement"
        },
        "scratchpad_entries": [
            {"entry_type": "hypothesis", "content": "Phonon coupling might be amplified under pressure."},
            {"entry_type": "finding", "content": "Sample synthesized at 15 GPa."}
        ],
        "turn_history": [
            {"user_message": "What is the critical temperature?", "assistant_message": "Reported at 150K under pressure."}
        ],
        "knowledge_memories": [
            {"knowledge_type": "canonical_fact", "content": "BCS theory predicts Cooper pair condensation."}
        ],
        "research_evidence": [
            {"retriever": "arxiv", "content": "Paper 2401.9999 shows zero resistance up to 130K."}
        ],
        "output_graph": {"nodes": [{"id": "n1"}], "edges": []}
    }

    formatted = format_research_context(context_dict)

    assert "=== RESEARCH CONTEXT AND WORKING STATE ===" in formatted
    assert f"- Workspace: {workspace_id}" in formatted
    assert f"- Conversation: {conversation_id}" in formatted
    assert "- Token Budget: 1250/8000" in formatted
    assert "Bounded Prior Turns:" in formatted
    assert "What is the critical temperature?" in formatted
    assert "Working Memory State:" in formatted
    assert "focus: cuprate perovksites" in formatted
    assert "Active Scratchpad Hypotheses:" in formatted
    assert "Phonon coupling might be amplified" in formatted
    assert "Accepted Knowledge Memories:" in formatted
    assert "BCS theory predicts Cooper pair" in formatted
    assert "Prior Research Evidence & Graph Summary:" in formatted
    assert "Paper 2401.9999 shows zero resistance" in formatted
    assert "Output Graph: present" in formatted
    assert "Current Objective: Investigate ambient superconductor mechanisms" in formatted
    assert "=== END RESEARCH CONTEXT AND WORKING STATE ===" in formatted


def test_format_research_context_empty_or_none():
    assert format_research_context(None) == ""
    assert format_research_context({}) == ""


def test_format_research_context_pydantic_model():
    mock_model = MagicMock()
    mock_model.model_dump.return_value = {
        "workspace_id": "ws-123",
        "query": "Quantum dot emitters",
        "turn_history": [{"user_message": "Query 1", "assistant_message": "Response 1"}]
    }

    formatted = format_research_context(mock_model)
    assert "=== RESEARCH CONTEXT AND WORKING STATE ===" in formatted
    assert "Query 1" in formatted


def test_format_research_context_with_role_based_turns_and_tagged_entries():
    context_dict = {
        "budget": 6000,
        "total_tokens": 1500,
        "version": "v2",
        "turn_history": [
            {"role": "user", "content": "Explain topological quantum computing"},
            {"role": "assistant", "content": "It relies on Majorana zero modes."}
        ],
        "scratchpad_entries": [{"entry_type": "hypothesis", "content": "Majorana bound states exist in nanowires."}],
        "knowledge_memories": [{"knowledge_type": "canonical_fact", "content": "Kitaev chain model predicts edge modes."}],
        "research_evidence": [{"retriever": "arxiv", "content": "Nanowire experiment 2024 results."}],
        "output_graph": {"nodes": [{"id": "n1"}, {"id": "n2"}], "edges": [{"source": "n1", "target": "n2"}]}
    }

    formatted = format_research_context(context_dict)

    assert "- Token Budget: 1500/6000" in formatted
    assert "- Context Version: v2" in formatted
    assert "User: Explain topological quantum computing" in formatted
    assert "Assistant: It relies on Majorana zero modes." in formatted
    assert "[hypothesis] Majorana bound states" in formatted
    assert "[canonical_fact] Kitaev chain model" in formatted
    assert "[arxiv] Nanowire experiment" in formatted
    assert "Output Graph: present (2 nodes, 1 edges)" in formatted


def test_build_prior_evidence_context_is_bounded_and_empty_safe():
    assert build_prior_evidence_context(None) == ""
    assert build_prior_evidence_context([]) == ""

    items = []
    for i in range(15):
        ev = MagicMock()
        ev.locator = f"https://example.com/{i}"
        ev.content = "x" * 2000
        items.append(ev)

    block = build_prior_evidence_context(items)
    assert block.startswith("PREVIOUS RESEARCH FINDINGS (Do not duplicate this work):")
    assert block.count("Source: ") == 10  # only the last 10 items
    assert "https://example.com/14" in block and "https://example.com/4" not in block
    assert "x" * 1500 + "..." in block and "x" * 1501 not in block  # snippets bounded to 1500 chars


# --------------------------------------------------------------------------- #
# ODR adapter contract
# --------------------------------------------------------------------------- #

def _engine_with_graph(astream):
    graph = MagicMock()
    graph.astream = astream
    with patch("app.integrations.research_engine.upstream.open_deep_research.deep_researcher.deep_researcher_builder.compile",
               return_value=graph):
        return OpenDeepResearchEngine(redis_client=MagicMock())


def _patched_persistence():
    """Patch usage-checkpoint persistence so the adapter test needs no database."""
    session_maker = patch("app.core.database.async_session_maker")
    repo_cls = patch("app.repositories.research.ResearchRepository")
    return session_maker, repo_cls


@pytest.mark.asyncio
async def test_astream_events_prepends_research_context_and_prior_evidence():
    captured = []

    async def mock_astream(initial_state, config, stream_mode="updates"):
        captured.append(initial_state["messages"][0]["content"])
        yield {"clarify_with_user": {}}

    engine = _engine_with_graph(mock_astream)
    sm, rc = _patched_persistence()
    with sm as session_maker, rc as repo_cls:
        session_maker.return_value.__aenter__.return_value = AsyncMock()
        repo_cls.return_value = AsyncMock()

        events = [e async for e in engine.astream_events(
            run_id=uuid4(),
            workspace_id=uuid4(),
            objective="Synthesize thermoelectric nanomaterials",
            research_context={
                "query": "Synthesize thermoelectric nanomaterials",
                "scratchpad_entries": [{"content": "Prior hypothesis note"}],
            },
            prior_evidence_context="PREVIOUS RESEARCH FINDINGS (Do not duplicate this work):\n\nSource: x\nfoo",
        )]

    content = captured[0]
    assert content.startswith("=== RESEARCH CONTEXT AND WORKING STATE ===")
    assert "=== OBJECTIVE ===" in content
    assert "Prior hypothesis note" in content
    assert "PREVIOUS RESEARCH FINDINGS" in content
    assert events[0]["status"] == "starting"
    assert events[1]["status"] == "planning"


@pytest.mark.asyncio
async def test_astream_events_yields_final_report_and_persists_nothing():
    report_text = "# Final Synthesis Report\nKey discovery: Topological insulator edge states."

    async def mock_astream(initial_state, config, stream_mode="updates"):
        yield {"final_report_generation": {"final_report": report_text}}

    engine = _engine_with_graph(mock_astream)
    sm, rc = _patched_persistence()
    with sm as session_maker, rc as repo_cls:
        session_maker.return_value.__aenter__.return_value = AsyncMock()
        repo = AsyncMock()
        repo_cls.return_value = repo

        events = [e async for e in engine.astream_events(run_id=uuid4(), workspace_id=uuid4(), objective="Objective")]

    statuses = [e["status"] for e in events]
    assert statuses == ["starting", "synthesizing", "final_report"]
    assert events[-1] == {"status": "final_report", "report": report_text}
    assert "summary" not in events[1] and "final_graph" not in events[1]
    # The engine hands the report over as data; it must not write reports/candidates itself.
    repo.create_report.assert_not_called()
    repo.create_artifact.assert_not_called()
    # And it never yields a terminal status.
    assert not {"completed", "failed", "partial", "cancelled", "aborted_by_timeline_fence"} & set(statuses)


@pytest.mark.asyncio
async def test_astream_events_raises_failures_instead_of_yielding_terminal_status():
    async def mock_astream(initial_state, config, stream_mode="updates"):
        raise RuntimeError("upstream exploded")
        yield  # pragma: no cover

    engine = _engine_with_graph(mock_astream)
    sm, rc = _patched_persistence()
    with sm as session_maker, rc as repo_cls:
        session_maker.return_value.__aenter__.return_value = AsyncMock()
        repo_cls.return_value = AsyncMock()

        seen = []
        with pytest.raises(RuntimeError, match="upstream exploded"):
            async for event in engine.astream_events(run_id=uuid4(), workspace_id=uuid4(), objective="Objective"):
                seen.append(event["status"])

    assert seen == ["starting"]


@pytest.mark.asyncio
async def test_astream_events_propagates_cancellation():
    started = asyncio.Event()

    async def mock_astream(initial_state, config, stream_mode="updates"):
        started.set()
        await asyncio.sleep(60)
        yield {"clarify_with_user": {}}  # pragma: no cover

    engine = _engine_with_graph(mock_astream)
    sm, rc = _patched_persistence()
    with sm as session_maker, rc as repo_cls:
        session_maker.return_value.__aenter__.return_value = AsyncMock()
        repo_cls.return_value = AsyncMock()

        async def consume():
            async for _ in engine.astream_events(run_id=uuid4(), workspace_id=uuid4(), objective="Objective"):
                pass

        task = asyncio.create_task(consume())
        await asyncio.wait_for(started.wait(), timeout=5)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task


# --------------------------------------------------------------------------- #
# ResearchService.finalize_report (engine-agnostic persistence)
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_finalize_report_creates_report_and_pending_review_candidate_no_autopromotion():
    workspace_id, run_id, evidence_id, turn_id = uuid4(), uuid4(), uuid4(), uuid4()

    ev = MagicMock()
    ev.evidence_id = evidence_id
    run = MagicMock()
    run.turn_id = turn_id
    run.engine = "open_deep_research"

    repo = AsyncMock()
    repo.list_evidence_for_run.return_value = [ev]
    repo.get_run.return_value = run

    service = ResearchService(repo)
    await service.finalize_report(workspace_id, run_id, "Objective", "# Report\nBody")

    repo.create_report.assert_called_once_with(
        workspace_id=workspace_id, run_id=run_id, objective="Objective", content="# Report\nBody"
    )
    repo.create_artifact.assert_called_once()
    kwargs = repo.create_artifact.call_args.kwargs
    assert kwargs["artifact_type"] == "memory_candidate"
    assert kwargs["promotion_status"] == "pending_review"

    payload = kwargs["payload"]
    assert payload["candidate_type"] == "memory_candidate"
    assert payload["text"] == "# Report\nBody"
    assert payload["proposed_memory_type"] == "research_memory"
    assert payload["provenance_version"] == "v2"
    assert payload["evidence_refs"] == [str(evidence_id)]
    assert {"ref_type": "research_evidence", "ref_id": str(evidence_id)} in payload["source_refs"]
    turn_refs = [r for r in payload["source_refs"] if r["ref_type"] == "conversation_turn"]
    assert [r["ref_id"] for r in turn_refs] == [str(turn_id)]
    assert payload["metadata"]["source"] == "open_deep_research"
    # No graph candidate: ODR does not produce a graph, and nothing is auto-promoted.
    assert repo.create_artifact.call_count == 1


@pytest.mark.asyncio
async def test_finalize_report_without_turn_or_evidence():
    repo = AsyncMock()
    repo.list_evidence_for_run.return_value = []
    run = MagicMock()
    run.turn_id = None
    run.engine = "open_deep_research"
    repo.get_run.return_value = run

    await ResearchService(repo).finalize_report(uuid4(), uuid4(), "Objective", "Report")

    payload = repo.create_artifact.call_args.kwargs["payload"]
    assert payload["evidence_refs"] == []
    assert payload["source_refs"] == []


# --------------------------------------------------------------------------- #
# Worker forwards resolved context to the engine
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_worker_task_passes_research_context_to_engine():
    """run_research_agent_job forwards research_context (and prior evidence) to engine.astream_events."""
    from app.workers.tasks import run_research_agent_job
    from app.models.workspace import Workspace

    workspace_id = uuid4()
    run_id = uuid4()
    user_id = uuid4()

    mock_redis = AsyncMock()
    ctx = {"job_id": "test_forward_ctx_job", "redis": mock_redis, "llm_call": AsyncMock(return_value="mock")}

    mock_run = MagicMock()
    mock_run.workspace_id = workspace_id
    mock_run.run_id = run_id
    mock_run.owner_id = user_id
    mock_run.engine = "open_deep_research"
    mock_run.conversation_id = None
    mock_run.turn_id = None
    mock_run.status = "pending"

    mock_ws = Workspace(workspace_id=workspace_id, owner_id=user_id)

    received = []

    async def mock_stream_events(*args, **kwargs):
        received.append((kwargs.get("research_context"), kwargs.get("prior_evidence_context")))
        yield {"status": "final_report", "report": "Report body"}

    mock_engine = MagicMock()
    mock_engine.astream_events = mock_stream_events

    prior = MagicMock()
    prior.locator = "https://example.com/prior"
    prior.content = "prior finding"

    with patch("app.workers.tasks.async_session_maker") as mock_session_cls, \
         patch("app.integrations.research_engine.factory.ResearchEngineFactory.get_engine", return_value=mock_engine), \
         patch("app.services.research.lifecycle.ResearchLifecycleService") as mock_lifecycle_cls, \
         patch("app.services.research.service.ResearchService.finalize_report", new_callable=AsyncMock) as mock_finalize, \
         patch("app.repositories.research.ResearchRepository") as mock_repo_cls:

        mock_lifecycle = mock_lifecycle_cls.return_value
        mock_lifecycle.transition_run = AsyncMock()

        mock_repo = mock_repo_cls.return_value
        mock_repo.get_run = AsyncMock(return_value=mock_run)
        mock_repo.list_candidates_by_status = AsyncMock(return_value=[])
        mock_repo.list_evidence_for_run = AsyncMock(return_value=[prior])

        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session

        exec_res = MagicMock()
        exec_res.scalars.return_value.first.side_effect = [mock_ws, mock_run, mock_run]
        mock_session.execute = AsyncMock(return_value=exec_res)

        test_context = {"query": "Forwarding test", "budget": 4000}
        res = await run_research_agent_job(
            ctx,
            workspace_id=str(workspace_id),
            objective="Forwarding test",
            run_id=str(run_id),
            research_context=test_context
        )

        assert res["status"] == "completed"
        assert len(received) == 1
        assert received[0][0] == test_context
        assert "https://example.com/prior" in received[0][1]
        mock_finalize.assert_awaited_once()
        assert mock_finalize.await_args.kwargs["report"] == "Report body"
        assert mock_finalize.await_args.kwargs["objective"] == "Forwarding test"


@pytest.mark.asyncio
async def test_worker_loads_research_context_from_turn_when_not_supplied():
    from app.workers.tasks import run_research_agent_job
    from app.models.workspace import Workspace

    workspace_id, run_id, user_id, turn_id = uuid4(), uuid4(), uuid4(), uuid4()
    ctx = {"job_id": "test_turn_ctx_job", "redis": AsyncMock(), "llm_call": AsyncMock(return_value="mock")}

    mock_run = MagicMock()
    mock_run.workspace_id = workspace_id
    mock_run.run_id = run_id
    mock_run.owner_id = user_id
    mock_run.engine = "open_deep_research"
    mock_run.conversation_id = None
    mock_run.turn_id = None  # no turn bridging in this test; context is loaded via a turn row below
    mock_run.status = "pending"

    mock_ws = Workspace(workspace_id=workspace_id, owner_id=user_id)

    received = []

    async def mock_stream_events(*args, **kwargs):
        received.append(kwargs.get("research_context"))
        yield {"status": "final_report", "report": "Report body"}

    mock_engine = MagicMock()
    mock_engine.astream_events = mock_stream_events

    mock_turn = MagicMock()
    mock_turn.context_version = {"research_context": {"query": "DB loaded query"}}
    mock_run.turn_id = turn_id

    with patch("app.workers.tasks.async_session_maker") as mock_session_cls, \
         patch("app.integrations.research_engine.factory.ResearchEngineFactory.get_engine", return_value=mock_engine), \
         patch("app.services.research.lifecycle.ResearchLifecycleService") as mock_lifecycle_cls, \
         patch("app.services.research.service.ResearchService.finalize_report", new_callable=AsyncMock), \
         patch("app.repositories.research.ResearchRepository") as mock_repo_cls, \
         patch("app.workers.tasks._bridge_chat_event", new_callable=AsyncMock, create=True):

        mock_lifecycle_cls.return_value.transition_run = AsyncMock()
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_run = AsyncMock(return_value=mock_run)
        mock_repo.list_candidates_by_status = AsyncMock(return_value=[])
        mock_repo.list_evidence_for_run = AsyncMock(return_value=[])

        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session
        mock_session.get = AsyncMock(return_value=mock_turn)

        exec_res = MagicMock()
        exec_res.scalars.return_value.first.side_effect = [mock_ws, mock_run, mock_run]
        mock_session.execute = AsyncMock(return_value=exec_res)

        await run_research_agent_job(
            ctx, workspace_id=str(workspace_id), objective="Fallback objective", run_id=str(run_id), research_context=None
        )

    assert received == [{"query": "DB loaded query"}]


def test_upstream_odr_files_remain_untouched():
    """Upstream ODR graph files do not import Chapter 4 models or promotion services."""
    import app.integrations.research_engine.upstream.open_deep_research.deep_researcher as dr_mod
    import app.integrations.research_engine.upstream.open_deep_research.configuration as config_mod

    dr_src = inspect.getsource(dr_mod)
    config_src = inspect.getsource(config_mod)

    prohibited_tokens = [
        "ResearchContext",
        "ConversationTurn",
        "PromotionService",
        "ResearchArtifact",
        "PromotionCandidate",
        "output_graph"
    ]
    for token in prohibited_tokens:
        assert token not in dr_src, f"Prohibited token {token} found in upstream deep_researcher.py"
        assert token not in config_src, f"Prohibited token {token} found in upstream configuration.py"
