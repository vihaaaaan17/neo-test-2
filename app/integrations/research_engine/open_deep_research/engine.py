import logging
import asyncio
from typing import AsyncGenerator, Any, Callable, Awaitable, Optional
from uuid import UUID

from app.integrations.research_engine.engine import ResearchEngine

logger = logging.getLogger(__name__)

class OpenDeepResearchEngine(ResearchEngine):
    """
    Adapter that integrates the Open Deep Research graph into Neosis as a ResearchEngine.
    It takes canonical Neosis objectives, runs them through ODR, and normalizes ODR 
    internal events back to Neosis ResearchEvents.
    """

    def __init__(
        self,
        llm_gateway: Callable[[str], Awaitable[str]],
        search_tool: Any,
        redis_client: Any = None
    ):
        self.llm_gateway = llm_gateway
        self.search_tool = search_tool
        self.redis_client = redis_client
        self._current_task = None
        
        # Compile graph lazily or here
        from app.integrations.research_engine.upstream.open_deep_research.deep_researcher import deep_researcher_builder
        from app.services.working_memory import get_checkpointer
        self.checkpointer = get_checkpointer()

        self.graph = deep_researcher_builder.compile(checkpointer=self.checkpointer)

    async def astream_events(
        self,
        run_id: UUID,
        workspace_id: UUID,
        objective: str,
        research_context: Optional[dict] = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Execute the ODR graph and normalize its events.

        Accepts an optional canonical ResearchContext snapshot (as produced by
        build_research_context / ConversationTurn.context_version). When provided,
        it is formatted into an authoritative RESEARCH CONTEXT AND WORKING STATE
        system block and prepended to the initial user objective message. This
        injects bounded prior turns, working memory, scratchpad, knowledge
        memories, and prior research evidence into the ODR graph WITHOUT
        modifying the upstream LangGraph topology.
        """
        yield {"status": "starting", "message": "Initializing Open Deep Research execution...", "run_id": str(run_id)}

        try:
            from app.integrations.research_engine.budget import UsageTracker, BudgetEnforcingCallbackHandler, ResearchBudgetExceeded
            from app.core.database import async_session_maker
            from app.repositories.research import ResearchRepository

            # Fetch existing evidence for this run_id (if this is a retry/continuation)
            async with async_session_maker() as session:
                repo = ResearchRepository(session)
                previous_evidence = await repo.list_evidence_for_run(workspace_id, run_id)

            objective_text = objective
            if previous_evidence:
                logger.info(f"Run {run_id} is a retry. Injecting {len(previous_evidence)} prior evidence items as context.")
                evidence_texts = []
                for ev in previous_evidence:
                    source = ev.locator or 'Unknown Source'
                    evidence_texts.append(f"Source: {source}\n{ev.content}")
                prior_context = "PREVIOUS RESEARCH FINDINGS (Do not duplicate this work):\n\n" + "\n\n---\n\n".join(evidence_texts)
                objective_text = f"{objective}\n\n{prior_context}"

            # If research_context is not provided directly, attempt to load it from the turn context_version
            if not research_context:
                try:
                    from app.models.research import ResearchRun
                    from app.models.conversation import ConversationTurn
                    async with async_session_maker() as session:
                        rr = await session.get(ResearchRun, run_id)
                        if rr and rr.turn_id:
                            turn = await session.get(ConversationTurn, rr.turn_id)
                            if turn and turn.context_version:
                                if isinstance(turn.context_version, dict):
                                    research_context = turn.context_version.get("research_context") or turn.context_version
                except Exception as e:
                    logger.warning(f"Could not load research_context from turn for run {run_id}: {e}")

            # Format canonical ResearchContext into an authoritative system block and
            # prepend it to the initial user objective message. This is the ONLY
            # mechanism by which Chapter 4 context reaches the ODR graph; upstream
            # ODR nodes, supervisor, researcher graphs, and prompts are untouched.
            context_block = self._format_research_context(research_context)
            if context_block:
                objective_text = f"{context_block}\n\n=== OBJECTIVE ===\n{objective_text}"

            initial_state = {
                "messages": [{"role": "user", "content": objective_text}]
            }
            
            tracker = UsageTracker()
            budget_callback = BudgetEnforcingCallbackHandler(tracker)
            
            # The config object maps to ODR's expected configuration
            config = {
                "configurable": {
                    "thread_id": str(run_id), # Group checkpointer by run_id
                    "search_api": "tavily", # Future: abstract this based on Neosis tools
                    "allow_clarification": False,
                    "research_model": "gpt-4o",
                    "usage_tracker": tracker, # Inject tracker for custom tools
                    "max_concurrent_research_units": 3,
                    "max_researcher_iterations": 2,
                    "max_react_tool_calls": 3,
                },
                "metadata": {
                    "owner": str(workspace_id),
                    "run_id": str(run_id)
                },
                "callbacks": [budget_callback]
            }
            
            # Try to run tracing if available
            try:
                from langchain_core.tracers.context import tracing_v2_enabled
                context_mgr = tracing_v2_enabled(project_name="NeosisLM-ResearchMode")
            except ImportError:
                import contextlib
                context_mgr = contextlib.nullcontext()
                
            with context_mgr:
                # Capture the current task so we can cancel it cooperatively if needed
                self._current_task = asyncio.current_task()
                
                async for step in self.graph.astream(initial_state, config, stream_mode="updates"):
                    node_name = list(step.keys())[0]
                    state = step[node_name]
                    
                    # Periodic checkpointing of usage
                    async with async_session_maker() as session:
                        repo = ResearchRepository(session)
                        await repo.create_usage(
                            workspace_id=workspace_id,
                            run_id=run_id,
                            model_calls=tracker.model_calls,
                            input_tokens=tracker.input_tokens,
                            output_tokens=tracker.output_tokens,
                            search_calls=tracker.search_calls,
                            estimation_type="exact_llm_callback"
                        )
                        
                        import json
                        logger.info(json.dumps({
                            "event": "research_usage_checkpoint",
                            "workspace_id": str(workspace_id),
                            "run_id": str(run_id),
                            "model_calls": tracker.model_calls,
                            "input_tokens": tracker.input_tokens,
                            "output_tokens": tracker.output_tokens,
                            "search_calls": tracker.search_calls
                        }))
                    
                    # Normalize LangGraph events to Neosis events
                    if node_name == "clarify_with_user":
                        yield {"status": "planning", "message": "Analyzing research objective"}
                    elif node_name == "write_research_brief":
                        brief = state.get("research_brief", "")
                        # Provide a short snippet for the message
                        snippet = brief[:100].replace("\n", " ") + "..." if brief else ""
                        yield {
                            "status": "planning",
                            "message": f"Generated research brief: {snippet}",
                            "scratchpad_entry": {
                                "entry_type": "investigation",
                                "content": f"Research brief: {brief}",
                                "metadata": {"node": "write_research_brief"}
                            }
                        }
                    elif node_name == "research_supervisor":
                        yield {
                            "status": "executing",
                            "message": "Supervisor delegating sub-tasks...",
                            "scratchpad_entry": {
                                "entry_type": "observation",
                                "content": "Research supervisor decomposed objective and delegated sub-tasks.",
                                "metadata": {"node": "research_supervisor"}
                            }
                        }
                    elif node_name == "final_report_generation":
                        report = state.get("final_report", "")

                        # Persist the final ResearchReport as canonical report state.
                        async with async_session_maker() as session:
                            repo = ResearchRepository(session)
                            await repo.create_report(
                                workspace_id=workspace_id,
                                run_id=run_id,
                                objective=objective,
                                content=report
                            )
                            # Emit a structured candidate artifact in pending_review
                            # conforming to the Phase 3 candidate envelope. Candidates
                            # are NEVER auto-promoted here: human review gates all
                            # transitions to KnowledgeMemory / Output KG.
                            all_evidence = await repo.list_evidence_for_run(workspace_id, run_id)
                            evidence_list = all_evidence or previous_evidence or []
                            evidence_refs = [
                                str(ev.evidence_id) for ev in evidence_list
                            ]
                            source_refs = [
                                {"ref_type": "research_evidence", "ref_id": str(ev.evidence_id)}
                                for ev in evidence_list
                            ]

                            # If run is bound to a conversation turn, add conversation_turn to provenance
                            run_obj = await repo.get_run(workspace_id, run_id)
                            if run_obj and run_obj.turn_id:
                                source_refs.append({
                                    "ref_type": "conversation_turn",
                                    "ref_id": str(run_obj.turn_id)
                                })

                            candidate_payload = {
                                "candidate_type": "memory_candidate",
                                "content": report,
                                "text": report,
                                "evidence_refs": evidence_refs,
                                "source_refs": source_refs,
                                "provenance": {
                                    "source_refs": evidence_refs,
                                    "derived_from_refs": evidence_refs,
                                    "derived_from": source_refs,
                                },
                                "proposed_memory_type": "research_memory",
                                "provenance_version": "v2",
                                "domain": "deep_research",
                                "metadata": {"source": "odr", "objective": objective},
                            }
                            await repo.create_artifact(
                                workspace_id=workspace_id,
                                run_id=run_id,
                                artifact_type="memory_candidate",
                                payload=candidate_payload,
                                promotion_status="pending_review",
                            )

                            # If graph state was synthesized, emit graph_candidate in pending_review
                            final_graph = state.get("final_graph") or state.get("graph")
                            if final_graph:
                                graph_payload = {
                                    "candidate_type": "graph_candidate",
                                    "nodes": final_graph.get("nodes", []) if isinstance(final_graph, dict) else [],
                                    "edges": final_graph.get("edges", []) if isinstance(final_graph, dict) else [],
                                    "evidence_refs": evidence_refs,
                                    "source_refs": source_refs,
                                    "provenance": {
                                        "source_refs": evidence_refs,
                                        "derived_from_refs": evidence_refs,
                                        "derived_from": source_refs,
                                    },
                                    "proposed_memory_type": "output_graph",
                                    "provenance_version": "v2",
                                    "domain": "deep_research",
                                    "metadata": {"source": "odr", "objective": objective},
                                }
                                if isinstance(final_graph, dict):
                                    for k, v in final_graph.items():
                                        if k not in graph_payload:
                                            graph_payload[k] = v
                                await repo.create_artifact(
                                    workspace_id=workspace_id,
                                    run_id=run_id,
                                    artifact_type="graph_candidate",
                                    payload=graph_payload,
                                    promotion_status="pending_review",
                                )

                        event_data = {
                            "status": "synthesizing",
                            "message": "Finalizing comprehensive report",
                            "summary": report
                        }
                        if state.get("final_graph") or state.get("graph"):
                            event_data["final_graph"] = state.get("final_graph") or state.get("graph")
                        yield event_data
                        
        except asyncio.CancelledError:
            logger.info(f"ODR execution cancelled for run {run_id}")
            yield {"status": "cancelled", "message": "Research execution cancelled."}
            raise
        except ResearchBudgetExceeded as e:
            logger.warning(f"Research budget exceeded for run {run_id}: {str(e)}")
            yield {"status": "partial", "message": f"Execution halted: {str(e)}"}
        except Exception as e:
            logger.exception(f"ODR Engine encountered an error for run {run_id}: {str(e)}")
            yield {"status": "failed", "message": f"ODR execution failed: {str(e)}"}
        finally:
            self._current_task = None
            
            # Final checkpoint of usage when execution ends
            try:
                # Note: tracker could be unbound if an error occurs early, handle gracefully
                if 'tracker' in locals():
                    async with async_session_maker() as session:
                        repo = ResearchRepository(session)
                        await repo.create_usage(
                            workspace_id=workspace_id,
                            run_id=run_id,
                            model_calls=tracker.model_calls,
                            input_tokens=tracker.input_tokens,
                            output_tokens=tracker.output_tokens,
                            search_calls=tracker.search_calls,
                            estimation_type="exact_llm_callback"
                        )
                        import json
                        logger.info(json.dumps({
                            "event": "research_usage_final",
                            "workspace_id": str(workspace_id),
                            "run_id": str(run_id),
                            "model_calls": tracker.model_calls,
                            "input_tokens": tracker.input_tokens,
                            "output_tokens": tracker.output_tokens,
                            "search_calls": tracker.search_calls
                        }))
            except Exception as e:
                logger.error(f"Failed to final persist usage for run {run_id}: {e}")

    @staticmethod
    def _format_research_context(research_context: Optional[dict]) -> str:
        """
        Formats a canonical ResearchContext snapshot (as produced by
        build_research_context / ConversationTurn.context_version) into an
        authoritative RESEARCH CONTEXT AND WORKING STATE system block.

        This is the ONLY mechanism by which Chapter 4 context reaches the ODR
        graph. Upstream ODR nodes, supervisor, researcher graphs, and prompts
        remain 100% untouched.

        Returns an empty string when no research_context is provided so callers
        can conditionally prepend the block.
        """
        if not research_context:
            return ""

        def _summarize_entries(entries, key="content", max_chars=200):
            if not entries:
                return "  (none)"
            lines = []
            for entry in entries:
                if isinstance(entry, dict):
                    if key == "user_message" and ("user_message" in entry or "assistant_message" in entry):
                        u = entry.get("user_message", "")
                        a = entry.get("assistant_message", "")
                        if u and a:
                            value = f"User: {u} | Assistant: {a}"
                        elif u:
                            value = f"User: {u}"
                        elif a:
                            value = f"Assistant: {a}"
                        else:
                            value = entry.get("content") or ""
                    elif "role" in entry and "content" in entry:
                        value = f"{entry.get('role').capitalize()}: {entry.get('content')}"
                    elif "entry_type" in entry and "content" in entry:
                        value = f"[{entry.get('entry_type')}] {entry.get('content')}"
                    elif "knowledge_type" in entry and "content" in entry:
                        value = f"[{entry.get('knowledge_type')}] {entry.get('content')}"
                    elif "retriever" in entry and "content" in entry:
                        value = f"[{entry.get('retriever')}] {entry.get('content')}"
                    else:
                        value = entry.get(key) or entry.get("content") or entry.get("text") or ""
                else:
                    value = str(entry)
                if value:
                    snippet = str(value).strip().replace("\n", " ")
                    if len(snippet) > max_chars:
                        snippet = snippet[:max_chars] + "..."
                    lines.append(f"  - {snippet}")
            return "\n".join(lines) if lines else "  (none)"

        # Accept either a pydantic model_dump dict or a plain dict.
        ctx = research_context
        if not isinstance(ctx, dict):
            # Pydantic models expose model_dump(); fall back to dict() otherwise.
            ctx = ctx.model_dump() if hasattr(ctx, "model_dump") else dict(ctx)

        workspace_id = ctx.get("workspace_id")
        conversation_id = ctx.get("conversation_id")
        query = ctx.get("query", "")
        context_version = ctx.get("context_version") or {}
        working_memory = ctx.get("working_memory") or {}
        scratchpad_entries = ctx.get("scratchpad_entries") or []
        turn_history = ctx.get("turn_history") or []
        knowledge_memories = ctx.get("knowledge_memories") or []
        research_evidence = ctx.get("research_evidence") or []
        output_graph = ctx.get("output_graph")

        budget = context_version.get("budget") if isinstance(context_version, dict) else None
        total_tokens = context_version.get("total_tokens") if isinstance(context_version, dict) else None
        version = context_version.get("version") if isinstance(context_version, dict) else None

        if budget is None and "budget" in ctx:
            budget = ctx.get("budget")
        if total_tokens is None and "total_tokens" in ctx:
            total_tokens = ctx.get("total_tokens")
        if version is None and "version" in ctx:
            version = ctx.get("version")

        lines = ["=== RESEARCH CONTEXT AND WORKING STATE ==="]
        if workspace_id is not None:
            lines.append(f"- Workspace: {workspace_id}")
        if conversation_id is not None:
            lines.append(f"- Conversation: {conversation_id}")
        if version is not None:
            lines.append(f"- Context Version: {version}")
        if budget is not None and total_tokens is not None:
            lines.append(f"- Token Budget: {total_tokens}/{budget}")
        elif budget is not None:
            lines.append(f"- Token Budget: {budget}")

        lines.append("")
        lines.append("Bounded Prior Turns:")
        lines.append(_summarize_entries(turn_history, key="user_message"))

        lines.append("")
        lines.append("Working Memory State:")
        if working_memory:
            wm_lines = [f"  - {k}: {v}" for k, v in working_memory.items()]
            lines.append("\n".join(wm_lines))
        else:
            lines.append("  (none)")

        lines.append("")
        lines.append("Active Scratchpad Hypotheses:")
        lines.append(_summarize_entries(scratchpad_entries, key="content"))

        lines.append("")
        lines.append("Accepted Knowledge Memories:")
        lines.append(_summarize_entries(knowledge_memories, key="content"))

        lines.append("")
        lines.append("Prior Research Evidence & Graph Summary:")
        lines.append(_summarize_entries(research_evidence, key="content"))
        if output_graph:
            node_count = len(output_graph.get("nodes", [])) if isinstance(output_graph, dict) and "nodes" in output_graph else None
            edge_count = len(output_graph.get("edges", [])) if isinstance(output_graph, dict) and "edges" in output_graph else None
            if node_count is not None and edge_count is not None:
                lines.append(f"  Output Graph: present ({node_count} nodes, {edge_count} edges)")
            else:
                lines.append("  Output Graph: present (projected workspace graph)")
        else:
            lines.append("  Output Graph: (none)")

        lines.append("")
        lines.append(f"Current Objective: {query}")
        lines.append("=== END RESEARCH CONTEXT AND WORKING STATE ===")

        return "\n".join(lines)

    async def cancel(self) -> None:
        """
        Trigger cooperative cancellation of the running execution.
        """
        if self._current_task and not self._current_task.done():
            self._current_task.cancel()
