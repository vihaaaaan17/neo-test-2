import logging
from typing import AsyncGenerator, Any, Optional
from uuid import UUID

from app.integrations.research_engine.engine import ResearchEngine
from app.services.research.context import format_research_context

logger = logging.getLogger(__name__)


class OpenDeepResearchEngine(ResearchEngine):
    """
    Thin adapter that runs the upstream Open Deep Research graph as a Neosis ResearchEngine.

    Contract with the worker (the worker owns terminal state, persistence and finalization):
      * yields progress events (`starting`, `planning`, `executing`, `synthesizing`);
      * yields exactly one `{"status": "final_report", "report": <markdown>}` when ODR produces its report;
      * never yields terminal statuses and never persists reports/candidates - failures are raised
        (`ResearchBudgetExceeded`, `asyncio.CancelledError`, or any other exception).
    """

    def __init__(self, redis_client: Any = None):
        self.redis_client = redis_client

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
        prior_evidence_context: str = "",
        **kwargs: Any,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Execute the ODR graph and normalize its events.

        The worker resolves the canonical ResearchContext snapshot and any retry evidence and passes them
        in as plain data. The context is formatted into an authoritative RESEARCH CONTEXT AND WORKING STATE
        block and prepended to the initial user message WITHOUT modifying the upstream LangGraph topology.
        """
        yield {"status": "starting", "message": "Initializing Open Deep Research execution...", "run_id": str(run_id)}

        tracker = None
        async_session_maker = None
        ResearchRepository = None
        try:
            from app.integrations.research_engine.budget import UsageTracker, BudgetEnforcingCallbackHandler
            from app.core.database import async_session_maker
            from app.repositories.research import ResearchRepository

            objective_text = objective
            if prior_evidence_context:
                logger.info(f"Run {run_id} is a retry. Injecting bounded prior evidence context.")
                objective_text = f"{objective}\n\n{prior_evidence_context}"

            # Format canonical ResearchContext into an authoritative system block and
            # prepend it to the initial user objective message. This is the ONLY
            # mechanism by which Chapter 4 context reaches the ODR graph; upstream
            # ODR nodes, supervisor, researcher graphs, and prompts are untouched.
            context_block = format_research_context(research_context)
            if context_block:
                objective_text = f"{context_block}\n\n=== OBJECTIVE ===\n{objective_text}"

            initial_state = {
                "messages": [{"role": "user", "content": objective_text}]
            }

            from app.core.config import settings, resolve_llm_provider
            import os

            # Provider resolution lives in one place; app.core.config already exported the
            # OpenAI-compatible env vars upstream ODR reads, so the adapter writes no environment.
            provider = resolve_llm_provider()
            active_key = provider.api_key or ""
            active_model = provider.model
            tavily_key = settings.TAVILY_API_KEY or os.environ.get("TAVILY_API_KEY", "")

            model_id = f"openai:{active_model}" if not active_model.startswith("openai:") else active_model

            tracker = UsageTracker()
            budget_callback = BudgetEnforcingCallbackHandler(tracker)

            # The config object maps to ODR's expected configuration
            config = {
                "configurable": {
                    "thread_id": f"{workspace_id}:{run_id}",  # Group checkpointer strictly by workspace_id and run_id
                    "search_api": "tavily",  # Future: abstract this based on Neosis tools

                    "allow_clarification": False,
                    "research_model": model_id,
                    "summarization_model": model_id,
                    "final_report_model": model_id,
                    "compression_model": model_id,
                    "apiKeys": {
                        "OPENAI_API_KEY": active_key,
                        "NVIDIA_API_KEY": active_key,
                        "TAVILY_API_KEY": tavily_key,
                    },
                    "usage_tracker": tracker,  # Inject tracker for custom tools
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

            import contextlib
            if os.environ.get("LANGCHAIN_TRACING_V2", "").lower() == "true" and os.environ.get("LANGCHAIN_API_KEY"):
                try:
                    from langchain_core.tracers.context import tracing_v2_enabled
                    context_mgr = tracing_v2_enabled(project_name="NeosisLM-ResearchMode")
                except ImportError:
                    context_mgr = contextlib.nullcontext()
            else:
                context_mgr = contextlib.nullcontext()

            with context_mgr:
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
                        yield {"status": "synthesizing", "message": "Finalizing comprehensive report"}
                        # Hand the report to the worker as data; the worker persists it and owns terminal state.
                        yield {"status": "final_report", "report": report}

        finally:
            # Final checkpoint of usage when execution ends (success, failure or cancellation)
            try:
                if tracker is not None and async_session_maker is not None:
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

    async def cancel(self) -> None:
        """
        ODR has no upstream cancellation API. The worker cancels the task that consumes
        astream_events, which cancels the awaiting LangGraph run; nothing more to do here.
        """
        return None
