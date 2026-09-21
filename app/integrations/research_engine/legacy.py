from typing import AsyncGenerator, Any, Callable, Awaitable
from uuid import UUID

from app.integrations.research_engine.engine import ResearchEngine
from app.orchestration.research_mode import ResearchModeOrchestrator

from typing_extensions import deprecated

@deprecated("This legacy research engine adapter is deprecated. Use OpenDeepResearchEngine instead.")
class LegacyResearchEngine(ResearchEngine):
    """
    Adapter that wraps the existing ResearchModeOrchestrator to conform to the 
    unified ResearchEngine interface.
    """

    def __init__(self, llm_gateway: Callable[[str], Awaitable[str]], search_tool: Any):
        self.orchestrator = ResearchModeOrchestrator(
            llm_gateway=llm_gateway,
            search_tool=search_tool
        )

    async def astream_events(self, run_id: UUID, workspace_id: UUID, objective: str) -> AsyncGenerator[dict[str, Any], None]:
        """
        Stream events from the legacy orchestrator. The legacy orchestrator doesn't
        natively take run_id, so we just pass workspace_id and objective.
        """
        async for event in self.orchestrator.astream_events(workspace_id, objective):
            yield event

    async def cancel(self) -> None:
        """
        Legacy engine doesn't have native cooperative cancellation other than
        letting asyncio.CancelledError propagate through its yields.
        """
        pass
