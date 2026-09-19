import logging
from typing import Callable, Awaitable

from app.core.config import settings
from app.integrations.research_engine.engine import ResearchEngineProtocol

logger = logging.getLogger(__name__)

def get_research_engine(
    workspace_flag: str,
    llm_gateway: Callable[[str], Awaitable[str]],
    search_tool: any
) -> ResearchEngineProtocol:
    """
    Factory function to route traffic to the appropriate Research Engine.
    Evaluates both the global env var and the workspace flag.
    """
    if settings.ENABLE_ADVANCED_RESEARCH and workspace_flag == "new":
        logger.info("Instantiating advanced OpenDeepResearchEngine")
        from app.integrations.research_engine.engine import OpenDeepResearchEngine
        return OpenDeepResearchEngine(llm_gateway=llm_gateway, search_tool=search_tool)
    else:
        logger.info("Instantiating legacy ResearchModeOrchestrator")
        from app.orchestration.research_mode import ResearchModeOrchestrator
        return ResearchModeOrchestrator(
            llm_gateway=llm_gateway,
            search_tool=search_tool
        )
