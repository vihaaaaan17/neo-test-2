import logging
import json
from typing import TypedDict, Callable, Awaitable, Any, List
from uuid import UUID
from langgraph.graph import StateGraph, END
from app.services.web_search import WebSearchTool
from app.schemas.graph import OutputGraph

logger = logging.getLogger(__name__)

class ResearchState(TypedDict):
    workspace_id: UUID
    objective: str
    plan: List[str]
    current_task_index: int
    gathered_evidence: List[str]
    final_graph: dict | None

class ResearchModeOrchestrator:
    def __init__(
        self,
        llm_gateway: Callable[[str], Awaitable[str]],
        search_tool: WebSearchTool
    ):
        self.llm_gateway = llm_gateway
        self.search_tool = search_tool
        self.graph = self._build_graph()
        
    def _build_graph(self):
        workflow = StateGraph(ResearchState)
        
        workflow.add_node("planner", self.planner_node)
        workflow.add_node("executor", self.executor_node)
        workflow.add_node("synthesizer", self.synthesizer_node)
        
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
        
        workflow.add_edge("synthesizer", END)
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
            "plan": plan,
            "current_task_index": 0,
            "gathered_evidence": []
        }
        
    async def executor_node(self, state: ResearchState) -> dict:
        idx = state.get("current_task_index", 0)
        plan = state.get("plan", [])
        evidence = list(state.get("gathered_evidence", []))
        
        if idx < len(plan):
            query = plan[idx]
            logger.info(f"Executing search {idx+1}/{len(plan)}: {query}")
            search_result = await self.search_tool.search(query)
            evidence.append(f"### Query: {query}\n{search_result}")
            
        return {
            "current_task_index": idx + 1,
            "gathered_evidence": evidence
        }
        
    def executor_router(self, state: ResearchState) -> str:
        idx = state.get("current_task_index", 0)
        plan = state.get("plan", [])
        if idx < len(plan):
            return "continue"
        return "finish"
        
    async def synthesizer_node(self, state: ResearchState) -> dict:
        logger.info("Synthesizing gathered evidence into OutputGraph")
        evidence_text = "\n\n".join(state.get("gathered_evidence", []))
        
        prompt = (
            "You are a research synthesis agent.\n"
            "Based on the following gathered evidence, build a curated knowledge graph representing the findings.\n"
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
        
    async def run(self, workspace_id: UUID, objective: str) -> ResearchState:
        initial_state = {
            "workspace_id": workspace_id,
            "objective": objective,
            "plan": [],
            "current_task_index": 0,
            "gathered_evidence": [],
            "final_graph": None
        }
        final_state = await self.graph.ainvoke(initial_state)
        return final_state
