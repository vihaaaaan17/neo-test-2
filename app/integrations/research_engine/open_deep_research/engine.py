import logging
import asyncio
from typing import AsyncGenerator, Any, Callable, Awaitable
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
        from langgraph.checkpoint.memory import MemorySaver
        from app.core.config import settings

        # Use AsyncPostgresSaver for production if available, MemorySaver for dev
        if settings.ASYNC_POSTGRES_SAVER_ENABLED:
            try:
                from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
                # Thread ID is passed per-execution in config, never in checkpointer constructor
                self.checkpointer = AsyncPostgresSaver.from_conn_string(settings.POSTGRES_DSN)
            except Exception as e:
                logger.warning(f"AsyncPostgresSaver unavailable ({e}); falling back to MemorySaver")
                self.checkpointer = MemorySaver()
        else:
            self.checkpointer = MemorySaver()

        self.graph = deep_researcher_builder.compile(checkpointer=self.checkpointer)

    async def astream_events(self, run_id: UUID, workspace_id: UUID, objective: str) -> AsyncGenerator[dict[str, Any], None]:
        """
        Execute the ODR graph and normalize its events.
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
                        yield {"status": "planning", "message": f"Generated research brief: {snippet}"}
                    elif node_name == "research_supervisor":
                        yield {"status": "executing", "message": "Supervisor delegating sub-tasks..."}
                    elif node_name == "final_report_generation":
                        report = state.get("final_report", "")
                        
                        # Persist the final ResearchReport and Candidates
                        async with async_session_maker() as session:
                            repo = ResearchRepository(session)
                            await repo.create_report(
                                workspace_id=workspace_id,
                                run_id=run_id,
                                objective=objective,
                                content=report
                            )
                            # Create a memory candidate artifact so the final promotion step can pick it up
                            await repo.create_artifact(
                                workspace_id=workspace_id,
                                run_id=run_id,
                                artifact_type="memory_candidate",
                                payload={"text": report, "domain": "deep_research", "metadata": {"source": "odr"}}
                            )
                            
                        yield {"status": "synthesizing", "message": "Finalizing comprehensive report", "summary": report}
                        
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

    async def cancel(self) -> None:
        """
        Trigger cooperative cancellation of the running execution.
        """
        if self._current_task and not self._current_task.done():
            self._current_task.cancel()
