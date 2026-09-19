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
    Phase 1 dummy implementation. Real wiring happens in Ticket 05.
    """
    def __init__(self, llm_gateway: Any, search_tool: Any):
        self.llm_gateway = llm_gateway
        self.search_tool = search_tool
        
    async def astream_events(self, workspace_id: UUID, objective: str) -> AsyncGenerator[dict[str, Any], None]:
        yield {"status": "starting", "message": "Starting advanced ODR engine (dummy for Phase 1)"}
        yield {"status": "planning", "message": "Dummy ODR planning phase"}
        yield {"status": "synthesizing", "message": "Dummy synthesis", "final_graph": {"nodes": [], "edges": []}}

