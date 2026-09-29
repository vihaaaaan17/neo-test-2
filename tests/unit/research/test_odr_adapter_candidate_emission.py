import pytest
import inspect
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from app.integrations.research_engine.open_deep_research.engine import OpenDeepResearchEngine


def test_format_research_context_full():
    """Verify _format_research_context formats all canonical context sections into an authoritative block."""
    workspace_id = uuid4()
    conversation_id = uuid4()

    context_dict = {
        "workspace_id": str(workspace_id),
        "conversation_id": str(conversation_id),
        "query": "Investigate ambient superconductor mechanisms",
        "context_version": {
            "version": "v1",
            "budget": 8000,
            "total_tokens": 1250,
        },
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

    formatted = OpenDeepResearchEngine._format_research_context(context_dict)

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
    """Verify passing None or empty dictionary returns an empty string."""
    assert OpenDeepResearchEngine._format_research_context(None) == ""
    assert OpenDeepResearchEngine._format_research_context({}) == ""


def test_format_research_context_pydantic_model():
    """Verify _format_research_context accepts an object with model_dump()."""
    mock_model = MagicMock()
    mock_model.model_dump.return_value = {
        "workspace_id": "ws-123",
        "query": "Quantum dot emitters",
        "turn_history": [{"user_message": "Query 1", "assistant_message": "Response 1"}]
    }

    formatted = OpenDeepResearchEngine._format_research_context(mock_model)
    assert "=== RESEARCH CONTEXT AND WORKING STATE ===" in formatted
    assert "- Workspace: ws-123" in formatted
    assert "Query 1" in formatted


@pytest.mark.asyncio
async def test_astream_events_prepends_research_context():
    """Verify astream_events formats and prepends research_context to initial_state messages."""
    mock_llm_gateway = AsyncMock()
    mock_search_tool = MagicMock()
    mock_redis = MagicMock()

    with patch("app.integrations.research_engine.upstream.open_deep_research.deep_researcher.deep_researcher_builder.compile") as mock_compile:
        mock_graph = MagicMock()

        async def mock_astream(initial_state, config, stream_mode="updates"):
            # Verify initial_state contains prepended context block
            messages = initial_state.get("messages", [])
            assert len(messages) == 1
            content = messages[0]["content"]
            assert content.startswith("=== RESEARCH CONTEXT AND WORKING STATE ===")
            assert "=== OBJECTIVE ===" in content
            assert "Synthesize thermoelectric nanomaterials" in content
            assert "Prior hypothesis note" in content
            yield {"clarify_with_user": {}}

        mock_graph.astream = mock_astream
        mock_compile.return_value = mock_graph

        engine = OpenDeepResearchEngine(
            llm_gateway=mock_llm_gateway,
            search_tool=mock_search_tool,
            redis_client=mock_redis
        )

        research_context = {
            "query": "Synthesize thermoelectric nanomaterials",
            "scratchpad_entries": [{"content": "Prior hypothesis note"}]
        }

        run_id = uuid4()
        workspace_id = uuid4()

        with patch("app.core.database.async_session_maker") as mock_session_maker:
            mock_session = AsyncMock()
            mock_session_maker.return_value.__aenter__.return_value = mock_session
            mock_repo = AsyncMock()
            mock_repo.list_evidence_for_run.return_value = []

            with patch("app.repositories.research.ResearchRepository", return_value=mock_repo):
                events = []
                async for event in engine.astream_events(
                    run_id=run_id,
                    workspace_id=workspace_id,
                    objective="Synthesize thermoelectric nanomaterials",
                    research_context=research_context
                ):
                    events.append(event)

                assert len(events) >= 2
                assert events[0]["status"] == "starting"
                assert events[1]["status"] == "planning"


@pytest.mark.asyncio
async def test_astream_events_db_fallback_loading():
    """Verify that when research_context=None, astream_events loads it from turn.context_version."""
    mock_llm_gateway = AsyncMock()
    mock_search_tool = MagicMock()
    mock_redis = MagicMock()

    with patch("app.integrations.research_engine.upstream.open_deep_research.deep_researcher.deep_researcher_builder.compile") as mock_compile:
        mock_graph = MagicMock()

        captured_content = []

        async def mock_astream(initial_state, config, stream_mode="updates"):
            messages = initial_state.get("messages", [])
            captured_content.append(messages[0]["content"])
            yield {"clarify_with_user": {}}

        mock_graph.astream = mock_astream
        mock_compile.return_value = mock_graph

        engine = OpenDeepResearchEngine(
            llm_gateway=mock_llm_gateway,
            search_tool=mock_search_tool,
            redis_client=mock_redis
        )

        run_id = uuid4()
        workspace_id = uuid4()
        turn_id = uuid4()

        mock_run = MagicMock()
        mock_run.turn_id = turn_id

        mock_turn = MagicMock()
        mock_turn.context_version = {
            "research_context": {
                "query": "DB loaded query",
                "scratchpad_entries": [{"content": "DB loaded scratchpad note"}]
            }
        }

        with patch("app.core.database.async_session_maker") as mock_session_maker:
            mock_session = AsyncMock()
            mock_session_maker.return_value.__aenter__.return_value = mock_session

            # session.get returns mock_run for run_id, and mock_turn for turn_id
            def mock_get(model, pk):
                if pk == run_id:
                    return mock_run
                elif pk == turn_id:
                    return mock_turn
                return None

            mock_session.get.side_effect = mock_get

            mock_repo = AsyncMock()
            mock_repo.list_evidence_for_run.return_value = []

            with patch("app.repositories.research.ResearchRepository", return_value=mock_repo):
                async for _ in engine.astream_events(
                    run_id=run_id,
                    workspace_id=workspace_id,
                    objective="DB fallback test objective",
                    research_context=None
                ):
                    pass

                assert len(captured_content) == 1
                assert "DB loaded scratchpad note" in captured_content[0]
                assert "DB fallback test objective" in captured_content[0]


@pytest.mark.asyncio
async def test_final_report_generation_emits_pending_review_candidate_no_autopromotion():
    """Verify that final_report_generation creates memory_candidate in pending_review with zero auto-promotion."""
    mock_llm_gateway = AsyncMock()
    mock_search_tool = MagicMock()
    mock_redis = MagicMock()

    with patch("app.integrations.research_engine.upstream.open_deep_research.deep_researcher.deep_researcher_builder.compile") as mock_compile:
        mock_graph = MagicMock()

        report_text = "# Final Synthesis Report\nKey discovery: Topological insulator edge states."

        async def mock_astream(initial_state, config, stream_mode="updates"):
            yield {
                "final_report_generation": {
                    "final_report": report_text
                }
            }

        mock_graph.astream = mock_astream
        mock_compile.return_value = mock_graph

        engine = OpenDeepResearchEngine(
            llm_gateway=mock_llm_gateway,
            search_tool=mock_search_tool,
            redis_client=mock_redis
        )

        run_id = uuid4()
        workspace_id = uuid4()
        evidence_id = uuid4()

        mock_ev = MagicMock()
        mock_ev.evidence_id = evidence_id

        with patch("app.core.database.async_session_maker") as mock_session_maker:
            mock_session = AsyncMock()
            mock_session_maker.return_value.__aenter__.return_value = mock_session

            mock_repo = AsyncMock()
            mock_repo.list_evidence_for_run.return_value = [mock_ev]
            mock_repo.create_report = AsyncMock()
            mock_repo.create_artifact = AsyncMock()

            with patch("app.repositories.research.ResearchRepository", return_value=mock_repo):
                events = []
                async for event in engine.astream_events(
                    run_id=run_id,
                    workspace_id=workspace_id,
                    objective="Explore topological insulators",
                    research_context=None
                ):
                    events.append(event)

                # Verify report creation
                mock_repo.create_report.assert_called_once_with(
                    workspace_id=workspace_id,
                    run_id=run_id,
                    objective="Explore topological insulators",
                    content=report_text
                )

                # Verify artifact creation in pending_review conforming to Phase 3 envelope
                mock_repo.create_artifact.assert_called_once()
                call_kwargs = mock_repo.create_artifact.call_args[1]
                assert call_kwargs["workspace_id"] == workspace_id
                assert call_kwargs["run_id"] == run_id
                assert call_kwargs["artifact_type"] == "memory_candidate"
                assert call_kwargs["promotion_status"] == "pending_review"

                payload = call_kwargs["payload"]
                assert payload["candidate_type"] == "memory_candidate"
                assert payload["content"] == report_text
                assert payload["text"] == report_text
                assert payload["proposed_memory_type"] == "research_memory"
                assert payload["provenance_version"] == "v2"
                assert str(evidence_id) in payload["evidence_refs"]
                assert payload["source_refs"][0]["ref_id"] == str(evidence_id)

                # Verify zero auto-promotion
                assert "promote" not in dir(mock_repo) or not mock_repo.promote.called


@pytest.mark.asyncio
async def test_final_report_generation_emits_graph_candidate_when_graph_in_state():
    """Verify that final_report_generation creates both memory_candidate and graph_candidate when graph is present."""
    mock_llm_gateway = AsyncMock()
    mock_search_tool = MagicMock()
    mock_redis = MagicMock()

    with patch("app.integrations.research_engine.upstream.open_deep_research.deep_researcher.deep_researcher_builder.compile") as mock_compile:
        mock_graph = MagicMock()

        report_text = "# Synthesis with Knowledge Graph\nIdentified 3 key compounds."
        graph_dict = {
            "nodes": [{"id": "compound_1", "label": "YBCO"}, {"id": "compound_2", "label": "BSCCO"}],
            "edges": [{"source": "compound_1", "target": "compound_2", "relation": "analogue"}]
        }

        async def mock_astream(initial_state, config, stream_mode="updates"):
            yield {
                "final_report_generation": {
                    "final_report": report_text,
                    "final_graph": graph_dict
                }
            }

        mock_graph.astream = mock_astream
        mock_compile.return_value = mock_graph

        engine = OpenDeepResearchEngine(
            llm_gateway=mock_llm_gateway,
            search_tool=mock_search_tool,
            redis_client=mock_redis
        )

        run_id = uuid4()
        workspace_id = uuid4()
        evidence_id = uuid4()

        mock_ev = MagicMock()
        mock_ev.evidence_id = evidence_id

        with patch("app.core.database.async_session_maker") as mock_session_maker:
            mock_session = AsyncMock()
            mock_session_maker.return_value.__aenter__.return_value = mock_session

            mock_repo = AsyncMock()
            mock_repo.list_evidence_for_run.return_value = [mock_ev]
            mock_repo.create_report = AsyncMock()
            mock_repo.create_artifact = AsyncMock()
            mock_repo.get_run = AsyncMock(return_value=None)

            with patch("app.repositories.research.ResearchRepository", return_value=mock_repo):
                events = []
                async for event in engine.astream_events(
                    run_id=run_id,
                    workspace_id=workspace_id,
                    objective="Synthesize materials graph",
                    research_context=None
                ):
                    events.append(event)

                # Expect 2 artifact creations: memory_candidate and graph_candidate
                assert mock_repo.create_artifact.call_count == 2
                artifact_calls = mock_repo.create_artifact.call_args_list

                # 1. memory_candidate
                mem_call = artifact_calls[0][1]
                assert mem_call["artifact_type"] == "memory_candidate"
                assert mem_call["promotion_status"] == "pending_review"
                assert mem_call["payload"]["candidate_type"] == "memory_candidate"
                assert mem_call["payload"]["proposed_memory_type"] == "research_memory"

                # 2. graph_candidate
                graph_call = artifact_calls[1][1]
                assert graph_call["artifact_type"] == "graph_candidate"
                assert graph_call["promotion_status"] == "pending_review"
                g_payload = graph_call["payload"]
                assert g_payload["candidate_type"] == "graph_candidate"
                assert g_payload["proposed_memory_type"] == "output_graph"
                assert len(g_payload["nodes"]) == 2
                assert len(g_payload["edges"]) == 1
                assert str(evidence_id) in g_payload["evidence_refs"]

                # Verify event contains final_graph
                assert len(events) >= 2
                synth_event = events[1]
                assert synth_event["status"] == "synthesizing"
                assert "final_graph" in synth_event


@pytest.mark.asyncio
async def test_final_report_generation_adds_conversation_turn_provenance():
    """Verify that when ResearchRun has turn_id, conversation_turn is included in provenance source_refs."""
    mock_llm_gateway = AsyncMock()
    mock_search_tool = MagicMock()

    with patch("app.integrations.research_engine.upstream.open_deep_research.deep_researcher.deep_researcher_builder.compile") as mock_compile:
        mock_graph = MagicMock()

        async def mock_astream(initial_state, config, stream_mode="updates"):
            yield {"final_report_generation": {"final_report": "Report content"}}

        mock_graph.astream = mock_astream
        mock_compile.return_value = mock_graph

        engine = OpenDeepResearchEngine(llm_gateway=mock_llm_gateway, search_tool=mock_search_tool)

        run_id = uuid4()
        workspace_id = uuid4()
        turn_id = uuid4()

        mock_run = MagicMock()
        mock_run.turn_id = turn_id

        with patch("app.core.database.async_session_maker") as mock_session_maker:
            mock_session = AsyncMock()
            mock_session_maker.return_value.__aenter__.return_value = mock_session

            mock_repo = AsyncMock()
            mock_repo.list_evidence_for_run.return_value = []
            mock_repo.create_report = AsyncMock()
            mock_repo.create_artifact = AsyncMock()
            mock_repo.get_run = AsyncMock(return_value=mock_run)

            with patch("app.repositories.research.ResearchRepository", return_value=mock_repo):
                async for _ in engine.astream_events(
                    run_id=run_id,
                    workspace_id=workspace_id,
                    objective="Objective",
                    research_context=None
                ):
                    pass

                mock_repo.create_artifact.assert_called_once()
                payload = mock_repo.create_artifact.call_args[1]["payload"]
                src_refs = payload["source_refs"]
                # Must include conversation_turn ref
                turn_refs = [r for r in src_refs if r.get("ref_type") == "conversation_turn"]
                assert len(turn_refs) == 1
                assert turn_refs[0]["ref_id"] == str(turn_id)


def test_format_research_context_with_role_based_turns_and_tagged_entries():
    """Verify formatting of role-based turn messages, tagged scratchpad, and output graph node/edge counts."""
    context_dict = {
        "budget": 6000,
        "total_tokens": 1500,
        "version": "v2",
        "turn_history": [
            {"role": "user", "content": "Explain topological quantum computing"},
            {"role": "assistant", "content": "It relies on Majorana zero modes."}
        ],
        "scratchpad_entries": [
            {"entry_type": "hypothesis", "content": "Majorana bound states exist in nanowires."}
        ],
        "knowledge_memories": [
            {"knowledge_type": "canonical_fact", "content": "Kitaev chain model predicts edge modes."}
        ],
        "research_evidence": [
            {"retriever": "arxiv", "content": "Nanowire experiment 2024 results."}
        ],
        "output_graph": {
            "nodes": [{"id": "n1"}, {"id": "n2"}],
            "edges": [{"source": "n1", "target": "n2"}]
        }
    }

    formatted = OpenDeepResearchEngine._format_research_context(context_dict)

    assert "- Token Budget: 1500/6000" in formatted
    assert "- Context Version: v2" in formatted
    assert "User: Explain topological quantum computing" in formatted
    assert "Assistant: It relies on Majorana zero modes." in formatted
    assert "[hypothesis] Majorana bound states" in formatted
    assert "[canonical_fact] Kitaev chain model" in formatted
    assert "[arxiv] Nanowire experiment" in formatted
    assert "Output Graph: present (2 nodes, 1 edges)" in formatted


@pytest.mark.asyncio
async def test_worker_task_passes_research_context_to_engine():
    """Verify that run_research_agent_job forwards research_context argument to engine.astream_events."""
    from app.workers.tasks import run_research_agent_job
    from app.models.workspace import Workspace

    workspace_id = uuid4()
    run_id = uuid4()
    user_id = uuid4()

    mock_redis = AsyncMock()
    ctx = {
        "job_id": "test_forward_ctx_job",
        "redis": mock_redis,
        "llm_call": AsyncMock(return_value="mock")
    }

    mock_run = MagicMock()
    mock_run.workspace_id = workspace_id
    mock_run.run_id = run_id
    mock_run.owner_id = user_id
    mock_run.engine = "open_deep_research"
    mock_run.conversation_id = None
    mock_run.turn_id = None
    mock_run.status = "pending"

    mock_ws = Workspace(workspace_id=workspace_id, owner_id=user_id)

    received_context = []

    async def mock_stream_events(*args, **kwargs):
        received_context.append(kwargs.get("research_context"))
        yield {"status": "completed"}

    mock_engine = MagicMock()
    mock_engine.astream_events = mock_stream_events

    with patch("app.workers.tasks.async_session_maker") as mock_session_cls, \
         patch("app.integrations.research_engine.factory.ResearchEngineFactory.get_engine", return_value=mock_engine), \
         patch("app.services.research.lifecycle.ResearchLifecycleService") as mock_lifecycle_cls, \
         patch("app.repositories.research.ResearchRepository") as mock_repo_cls:

        mock_lifecycle = mock_lifecycle_cls.return_value
        mock_lifecycle.transition_run = AsyncMock()

        mock_repo = mock_repo_cls.return_value
        mock_repo.get_run = AsyncMock(return_value=mock_run)
        mock_repo.list_candidates_by_status = AsyncMock(return_value=[])

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
        assert len(received_context) == 1
        assert received_context[0] == test_context


def test_upstream_odr_files_remain_untouched():
    """Verify that upstream ODR graph files do not import Chapter 4 models or promotion services."""
    import app.integrations.research_engine.upstream.open_deep_research.deep_researcher as dr_mod
    import app.integrations.research_engine.upstream.open_deep_research.configuration as config_mod

    dr_src = inspect.getsource(dr_mod)
    config_src = inspect.getsource(config_mod)

    # Ensure no Chapter 4 specific imports leak into upstream ODR
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

