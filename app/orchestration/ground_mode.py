import logging
from typing import TypedDict, Callable, Awaitable, Any
from uuid import UUID
from langgraph.graph import StateGraph, END
from app.services.hybrid_retrieval import HybridRetrievalService

logger = logging.getLogger(__name__)

class GroundModeState(TypedDict):
    workspace_id: UUID
    query: str
    query_embedding: list[float]
    context_bundle: dict
    answer: str
    evidence: list[UUID]
    is_grounded: bool
    retries: int

class GroundModeOrchestrator:
    def __init__(
        self, 
        hybrid_retriever: HybridRetrievalService,
        llm_gateway: Callable[[str], Awaitable[str]],
        embed_gateway: Callable[[str], Awaitable[list[float]]],
        memory_router: Any = None
    ):
        from app.services.memory_router import MemoryRouterService
        self.hybrid_retriever = hybrid_retriever
        self.llm_gateway = llm_gateway
        self.embed_gateway = embed_gateway
        self.memory_router = memory_router or MemoryRouterService()
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(GroundModeState)

        workflow.add_node("retrieve", self.retrieve_node)
        workflow.add_node("answer", self.answer_node)
        workflow.add_node("check_hallucination", self.check_hallucination_node)

        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "answer")
        workflow.add_edge("answer", "check_hallucination")
        
        workflow.add_conditional_edges(
            "check_hallucination",
            self.hallucination_router,
            {
                "continue": END,
                "retry": "answer"
            }
        )

        return workflow.compile()

    async def retrieve_node(self, state: GroundModeState) -> dict:
        logger.info(f"Retrieving context for query: {state['query']}")
        query_embedding = await self.embed_gateway(state["query"])
        
        chunks = await self.hybrid_retriever.retrieve(
            workspace_id=state["workspace_id"],
            query_text=state["query"],
            query_embedding=query_embedding
        )
        
        from app.schemas.context import MemoryItem
        items = [MemoryItem(id=str(c.block_id), type="source", text=c.text, metadata=c.metadata) for c in chunks]
        
        # Ground mode has strict budget
        bundle = self.memory_router.build_context(items, token_budget=4000)
        
        return {
            "query_embedding": query_embedding,
            "context_bundle": bundle.model_dump(),
            "retries": 0,
            "is_grounded": False,
            "answer": ""
        }

    async def answer_node(self, state: GroundModeState) -> dict:
        bundle_dict = state.get("context_bundle", {})
        items = bundle_dict.get("items", [])
        context_text = "\n\n".join(
            f"--- Context Block {item['id']} ---\n{item['text']}" for item in items
        )
        
        prompt = (
            "You are a strict research assistant. Answer the user's query ONLY using the provided context.\n"
            "If the context does not contain the answer, state that you cannot answer.\n\n"
            "You MUST output exactly valid JSON matching this schema:\n"
            "{\n"
            '  "answer": "Your detailed answer",\n'
            '  "evidence": ["UUID_of_context_block_1", "UUID_of_context_block_2"]\n'
            "}\n\n"
            f"Context:\n{context_text}\n\n"
            f"Query: {state['query']}"
        )
        
        if state.get("retries", 0) > 0:
            prompt += "\n\nCRITICAL INSTRUCTION: Your previous answer was flagged as hallucinated or using outside knowledge. Stick strictly to the context!"

        logger.info(f"Generating answer (Retry: {state.get('retries', 0)})")
        raw_answer = await self.llm_gateway(prompt)
        
        import json
        try:
            parsed = json.loads(raw_answer)
            answer = parsed.get("answer", "")
            evidence = parsed.get("evidence", [])
            # Convert strings to UUID objects if needed, or leave as strings if acceptable.
            # But the schema expects list[UUID], so let's cast them.
            evidence_uuids = [UUID(str(e)) for e in evidence]
        except Exception as e:
            logger.warning(f"Failed to parse LLM output as JSON: {e}")
            answer = raw_answer
            evidence_uuids = []
        
        return {"answer": answer, "evidence": evidence_uuids}

    async def check_hallucination_node(self, state: GroundModeState) -> dict:
        bundle_dict = state.get("context_bundle", {})
        items = bundle_dict.get("items", [])
        context_text = "\n\n".join(
            f"--- Context Block ---\n{item['text']}" for item in items
        )
        
        prompt = (
            "You are a hallucination detection judge.\n"
            "Evaluate if the following Answer is strictly and completely supported by the Context.\n"
            "Reply with exactly 'YES' if it is grounded, or 'NO' if it contains hallucinated facts or outside knowledge.\n\n"
            f"Context:\n{context_text}\n\n"
            f"Answer: {state['answer']}"
        )
        
        logger.info("Checking for hallucination...")
        eval_result = await self.llm_gateway(prompt)
        
        is_grounded = eval_result.strip().upper() == "YES"
        
        return {
            "is_grounded": is_grounded,
            "retries": state.get("retries", 0) + 1
        }

    def hallucination_router(self, state: GroundModeState) -> str:
        if state.get("is_grounded", False):
            return "continue"
        if state.get("retries", 0) > 1:
            logger.warning("Max retries reached. Returning ungrounded answer.")
            return "continue"
        
        logger.info("Hallucination detected. Retrying answer generation.")
        return "retry"

    async def run(self, workspace_id: UUID, query: str) -> GroundModeState:
        initial_state = {
            "workspace_id": workspace_id,
            "query": query,
            "query_embedding": [],
            "context_bundle": {},
            "answer": "",
            "evidence": [],
            "is_grounded": False,
            "retries": 0
        }
        final_state = await self.graph.ainvoke(initial_state)
        return final_state
