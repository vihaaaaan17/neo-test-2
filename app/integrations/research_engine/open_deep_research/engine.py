import logging
from typing import AsyncGenerator, Any, Optional
from uuid import UUID

from app.integrations.research_engine.engine import CONVERSATIONAL_STYLE, ResearchEngine, turn_response
from app.services.research.context import format_research_context

logger = logging.getLogger(__name__)

# Budget profiles expressed only through ODR's own configuration knobs plus the UsageTracker caps the adapter already
# enforces mid-run (ResearchBudgetExceeded). "balanced" is the previous fixed configuration.
# The *_model_max_tokens values are ODR's own per-call output caps (configuration.py; upstream defaults 10000/8192/10000).
# Live measurement (2026-10-10): with the upstream default, ODR's single final-answer call for "Who wrote Dune?" produced
# ~4.5k tokens and took 223 s on the free gateway - the cap bounds the dominant latency of conversational turns.
ODR_BUDGET_PROFILES: dict[str, dict[str, int]] = {
    "low": {"max_concurrent_research_units": 1, "max_researcher_iterations": 1, "max_react_tool_calls": 2,
            "research_model_max_tokens": 3000, "compression_model_max_tokens": 2000, "final_report_model_max_tokens": 1200,
            "max_model_calls": 30, "max_input_tokens": 200_000, "max_output_tokens": 30_000, "max_search_calls": 6},
    "balanced": {"max_concurrent_research_units": 3, "max_researcher_iterations": 2, "max_react_tool_calls": 3,
                 "research_model_max_tokens": 5000, "compression_model_max_tokens": 4000, "final_report_model_max_tokens": 2500,
                 "max_model_calls": 100, "max_input_tokens": 1_000_000, "max_output_tokens": 200_000, "max_search_calls": 50},
    "deep": {"max_concurrent_research_units": 4, "max_researcher_iterations": 3, "max_react_tool_calls": 5,
             "research_model_max_tokens": 10000, "compression_model_max_tokens": 8192, "final_report_model_max_tokens": 10000,
             "max_model_calls": 160, "max_input_tokens": 1_600_000, "max_output_tokens": 300_000, "max_search_calls": 80},
}
_ODR_NATIVE_KNOBS = ("max_concurrent_research_units", "max_researcher_iterations", "max_react_tool_calls",
                     "research_model_max_tokens", "compression_model_max_tokens", "final_report_model_max_tokens")


class OpenDeepResearchEngine(ResearchEngine):
    """
    Thin adapter that runs the upstream Open Deep Research graph as a Neosis ResearchEngine.

    Contract with the worker (the worker owns terminal state, persistence and finalization):
      * yields progress events (`starting`, `planning`, `executing`, `synthesizing`);
      * yields exactly one `turn_response` with ODR's final answer;
      * never yields terminal statuses and never persists reports/candidates - failures are raised
        (`ResearchBudgetExceeded`, `asyncio.CancelledError`, or any other exception).
    """

    def __init__(self, redis_client: Any = None, budget_profile: str = "balanced", token_ceiling: Optional[int] = None):
        self.redis_client = redis_client
        if budget_profile not in ODR_BUDGET_PROFILES:
            raise ValueError(f"Unknown ODR budget profile: {budget_profile!r}")
        self.budget_profile = budget_profile
        # Remaining measured-token allowance of the whole turn (set by the router); caps the profile's own limits.
        self.token_ceiling = token_ceiling

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
            from app.integrations.research_engine.budget import UsageTracker, BudgetEnforcingCallbackHandler, ModelTimingHandler
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

            # ODR's final-answer prompt takes the user's messages into account; the response-style instruction is
            # passed there (input only - the vendored ODR prompts are not modified).
            objective_text = f"{objective_text}\n\n{CONVERSATIONAL_STYLE}"

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

            profile = ODR_BUDGET_PROFILES[self.budget_profile]
            max_input = profile["max_input_tokens"]
            max_output = profile["max_output_tokens"]
            if self.token_ceiling is not None:
                max_input = min(max_input, self.token_ceiling)
                max_output = min(max_output, self.token_ceiling)
            tracker = UsageTracker(
                max_model_calls=profile["max_model_calls"],
                max_input_tokens=max_input,
                max_output_tokens=max_output,
                max_search_calls=profile["max_search_calls"],
            )
            timing = ModelTimingHandler()
            node_ms: dict[str, int] = {}
            import time as _time
            last_t = _time.monotonic()
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
                    **{knob: profile[knob] for knob in _ODR_NATIVE_KNOBS},
                },
                "metadata": {
                    "owner": str(workspace_id),
                    "run_id": str(run_id)
                },
                "callbacks": [budget_callback, timing]
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
                    now_t = _time.monotonic()
                    node_ms[node_name] = node_ms.get(node_name, 0) + int((now_t - last_t) * 1000)
                    last_t = now_t

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
                        yield {"status": "synthesizing", "message": "Writing the answer"}
                        yield {
                            "status": "metrics",
                            "budget_profile": self.budget_profile,
                            "node_ms": dict(node_ms),
                            "search_calls": tracker.search_calls,
                            "model_calls": tracker.model_calls,
                            "input_tokens": tracker.input_tokens,
                            "output_tokens": tracker.output_tokens,
                            "limits": {"max_model_calls": tracker.max_model_calls, "max_input_tokens": tracker.max_input_tokens,
                                       "max_output_tokens": tracker.max_output_tokens, "max_search_calls": tracker.max_search_calls,
                                       **{knob: profile[knob] for knob in _ODR_NATIVE_KNOBS}},
                            **timing.snapshot(),
                        }
                        # Hand the answer to the worker as data; the worker persists it and owns terminal state.
                        yield turn_response(report)

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
