from typing import Protocol, AsyncGenerator, Any
from uuid import UUID

class ResearchEngineProtocol(Protocol):
    async def astream_events(self, workspace_id: UUID, objective: str) -> AsyncGenerator[dict[str, Any], None]:
        """
        Streams execution events from the research engine.
        Each event is a dictionary containing at minimum 'status' and 'message' keys.
        Optional keys like 'final_graph' may be emitted when synthesis completes.
        """
        ...


class OpenDeepResearchEngine(ResearchEngineProtocol):
    """
    Phase 1 implementation for Open Deep Research Engine.
    Routes Neosis job parameters into ODR LangGraph inputs and yields standardized events.
    """
    def __init__(self, llm_gateway: Any, search_tool: Any, redis_client: Any = None):
        self.llm_gateway = llm_gateway
        self.search_tool = search_tool
        self.redis_client = redis_client
        
    async def astream_events(self, workspace_id: UUID, objective: str) -> AsyncGenerator[dict[str, Any], None]:
        yield {"status": "starting", "message": "Initializing Open Deep Research execution..."}
        
        try:
            from app.integrations.research_engine.upstream.open_deep_research.deep_researcher import deep_researcher_builder
            from langgraph.checkpoint.memory import MemorySaver
            
            # Use MemorySaver as a transient checkpoint for Phase 1 to leave Postgres untouched.
            # In a production deployment where langgraph-checkpoint-redis is installed, 
            # this would be replaced by AsyncRedisSaver(self.redis_client).
            checkpointer = MemorySaver()
            graph = deep_researcher_builder.compile(checkpointer=checkpointer)
            
            initial_state = {
                "messages": [{"role": "user", "content": objective}]
            }
            
            config = {
                "configurable": {
                    "thread_id": str(workspace_id),
                    "search_api": "tavily",
                    "allow_clarification": False,
                },
                "metadata": {
                    "owner": str(workspace_id)
                }
            }
            
            from langchain_core.tracers.context import tracing_v2_enabled
            with tracing_v2_enabled(project_name="NeosisLM-ResearchMode"):
                async for step in graph.astream(initial_state, config, stream_mode="updates"):
                    node_name = list(step.keys())[0]
                    state = step[node_name]
                    
                    if node_name == "clarify_with_user":
                        yield {"status": "planning", "message": "Analyzing research objective"}
                    elif node_name == "write_research_brief":
                        brief = state.get("research_brief", "")
                        yield {"status": "planning", "message": f"Generated research brief: {brief[:50]}..."}
                    elif node_name == "research_supervisor":
                        yield {"status": "executing", "message": "Supervisor delegating tasks..."}
                    elif node_name == "final_report_generation":
                        report = state.get("final_report", "")
                        yield {"status": "synthesizing", "message": "Finalizing comprehensive report", "summary": report}
                        
        except Exception as e:
            import logging
            logging.error(f"ODR Engine encountered an error: {str(e)}")
            yield {"status": "failed", "message": f"ODR execution failed: {str(e)}"}

