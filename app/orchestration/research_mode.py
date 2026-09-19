import logging
import json
from typing import TypedDict, Callable, Awaitable, Any, List
from uuid import UUID
from langgraph.graph import StateGraph, END
from app.services.web_search import WebSearchTool
from app.schemas.graph import OutputGraph

logger = logging.getLogger(__name__)

from pydantic import BaseModel

class ResearchContext(BaseModel):
    plan: List[str] = []
    current_task_index: int = 0
    gathered_evidence: List[str] = []

class ResearchState(TypedDict):
    workspace_id: UUID
    objective: str
    context: ResearchContext
    final_graph: dict | None
    summary: str | None

class ResearchModeOrchestrator:
    def __init__(
        self,
        llm_gateway: Callable[[str], Awaitable[str]],
        search_tool: WebSearchTool,
        memory_router: Any = None
    ):
        from app.services.memory_router import MemoryRouterService
        self.llm_gateway = llm_gateway
        self.search_tool = search_tool
        self.memory_router = memory_router or MemoryRouterService()
        self.graph = self._build_graph()
        
    def _build_graph(self):
        workflow = StateGraph(ResearchState)
        
        workflow.add_node("planner", self.planner_node)
        workflow.add_node("executor", self.executor_node)
        workflow.add_node("synthesizer", self.synthesizer_node)
        workflow.add_node("reporter", self.reporter_node)
        
        workflow.set_entry_point("planner")
        workflow.add_edge("planner", "executor")
        
        workflow.add_conditional_edges(
            "executor",
            self.executor_router,
            {
                "continue": "executor",
                "finish": "synthesizer"
            }
        )
        
        workflow.add_edge("synthesizer", "reporter")
        workflow.add_edge("reporter", END)
        return workflow.compile()
        
    async def planner_node(self, state: ResearchState) -> dict:
        logger.info(f"Planning research for objective: {state['objective']}")
        prompt = (
            "You are an expert research planner.\n"
            "Given the user's objective, break it down into a list of 2 to 4 specific web search queries.\n"
            "Return EXACTLY a JSON array of strings, and nothing else.\n\n"
            f"Objective: {state['objective']}\n\n"
            "JSON Array:"
        )
        
        raw_plan = await self.llm_gateway(prompt)
        try:
            clean_plan = raw_plan.strip().strip("`").removeprefix("json").strip()
            plan = json.loads(clean_plan)
            if not isinstance(plan, list):
                plan = [str(state["objective"])]
        except Exception as e:
            logger.warning(f"Failed to parse planner output, falling back to objective. Error: {e}")
            plan = [state["objective"]]
            
        return {
            "context": ResearchContext(
                plan=plan,
                current_task_index=0,
                gathered_evidence=[]
            )
        }
        
    async def executor_node(self, state: ResearchState) -> dict:
        ctx = state.get("context", ResearchContext())
        idx = ctx.current_task_index
        plan = ctx.plan
        evidence = list(ctx.gathered_evidence)
        
        if idx < len(plan):
            query = plan[idx]
            logger.info(f"Executing search {idx+1}/{len(plan)}: {query}")
            search_result = await self.search_tool.search(query)
            evidence.append(f"### Query: {query}\n{search_result}")
            
        return {
            "context": ResearchContext(
                plan=plan,
                current_task_index=idx + 1,
                gathered_evidence=evidence
            )
        }
        
    def executor_router(self, state: ResearchState) -> str:
        ctx = state.get("context", ResearchContext())
        if ctx.current_task_index < len(ctx.plan):
            return "continue"
        return "finish"
        
    async def synthesizer_node(self, state: ResearchState) -> dict:
        logger.info("Synthesizing gathered evidence into OutputGraph")
        ctx = state.get("context", ResearchContext())
        
        from app.schemas.context import MemoryItem
        import uuid
        
        # Treat each gathered evidence as a 'source' memory item
        items = [
            MemoryItem(id=str(uuid.uuid4()), type="source", text=ev, metadata={})
            for ev in ctx.gathered_evidence
        ]
        
        bundle = self.memory_router.build_context(items, token_budget=8000)
        
        evidence_text = "\n\n".join(item.text for item in bundle.items)
        
        prompt = (
            "You are a research synthesis agent.\n"
            "Based on the following gathered evidence, build a curated, highly-compressed knowledge graph representing the findings.\n"
            "CRITICAL: To prevent the graph from becoming too large, you MUST extract only the most important macro-level concepts and relationships. Do NOT include granular details or overly specific nodes.\n"
            "You MUST output exactly valid JSON matching the OutputGraph schema.\n"
            "The JSON must have 'nodes' (array of OutputGraphNode) and 'edges' (array of OutputGraphEdge).\n"
            "Each OutputGraphNode must have: 'id', 'label', 'properties' (dict).\n"
            "It may optionally have 'provenance' (dict with 'derived_from_refs' (array of UUID strings), 'calculation', 'verification_status').\n"
            "Each OutputGraphEdge must have: 'source_id', 'target_id', 'type', 'properties' (dict).\n\n"
            f"Objective: {state['objective']}\n\n"
            f"Evidence:\n{evidence_text}\n\n"
            "JSON Output:"
        )
        
        raw_graph = await self.llm_gateway(prompt)
        try:
            clean_graph = raw_graph.strip().strip("`").removeprefix("json").strip()
            graph_data = json.loads(clean_graph)
            
            # Validate through pydantic
            validated_graph = OutputGraph(**graph_data)
            final_graph = validated_graph.model_dump(mode="json")
            
        except Exception as e:
            logger.error(f"Failed to synthesize graph: {e}")
            final_graph = {"nodes": [], "edges": []}
            
        return {"final_graph": final_graph}

    async def reporter_node(self, state: ResearchState) -> dict:
        logger.info("Generating research summary")
        prompt = (
            "You are a research reporting agent.\n"
            "Based on the user's objective and the synthesized knowledge graph, write a concise, human-readable summary of the findings.\n\n"
            f"Objective: {state['objective']}\n\n"
            f"Knowledge Graph:\n{json.dumps(state.get('final_graph', {}))}\n\n"
            "Summary:"
        )
        summary = await self.llm_gateway(prompt)
        return {"summary": summary}
        
    async def astream_events(self, workspace_id: UUID, objective: str):
        initial_state = {
            "workspace_id": workspace_id,
            "objective": objective,
            "context": ResearchContext(),
            "final_graph": None,
            "summary": None
        }
        
        from langchain_core.tracers.context import tracing_v2_enabled
        with tracing_v2_enabled(project_name="NeosisLM-ResearchMode"):
            async for step in self.graph.astream(initial_state):
                node_name = list(step.keys())[0]
                state = step[node_name]
                if node_name == "planner":
                    ctx = state.get("context", ResearchContext())
                    yield {"status": "planning", "message": "Generated research plan", "plan": ctx.plan}
                elif node_name == "executor":
                    ctx = state.get("context", ResearchContext())
                    idx = ctx.current_task_index - 1
                    plan = ctx.plan
                    if idx < len(plan):
                        yield {"status": "executing", "message": f"Executed search: {plan[idx]}"}
                elif node_name == "synthesizer":
                    yield {"status": "synthesizing", "message": "Synthesized final graph", "final_graph": state.get("final_graph")}
                elif node_name == "reporter":
                    yield {"status": "reporting", "message": "Generated research summary", "summary": state.get("summary")}

    async def run(self, workspace_id: UUID, objective: str) -> ResearchState:
        initial_state = {
            "workspace_id": workspace_id,
            "objective": objective,
            "context": ResearchContext(),
            "final_graph": None,
            "summary": None
        }
        
        from langchain_core.tracers.context import tracing_v2_enabled
        with tracing_v2_enabled(project_name="NeosisLM-ResearchMode"):
            final_state = await self.graph.ainvoke(initial_state)
            
        return final_state
