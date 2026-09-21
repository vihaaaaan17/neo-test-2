import logging
from typing import Callable, Awaitable, Any

from app.integrations.research_engine.engine import ResearchEngine
from app.integrations.research_engine.legacy import LegacyResearchEngine
# OpenDeepResearchEngine will be imported when implemented in Ticket 02

logger = logging.getLogger(__name__)

class ResearchEngineFactory:
    """
    Central factory to resolve the correct ResearchEngine based on the run's engine field.
    """

    @staticmethod
    def get_engine(
        engine_name: str,
        llm_gateway: Callable[[str], Awaitable[str]],
        search_tool: Any,
        redis_client: Any = None
    ) -> ResearchEngine:
        from app.core.config import settings
        
        # Override with global flag if set
        if settings.ACTIVE_RESEARCH_ENGINE:
            engine_name = settings.ACTIVE_RESEARCH_ENGINE

        """
        Instantiate the requested research engine.
        
        Args:
            engine_name: The requested engine (e.g., 'legacy', 'open_deep_research').
            llm_gateway: Simple LLM callable for the orchestrators.
            search_tool: Search tool implementation.
            redis_client: Optional redis client for streaming/state.
        """
        if engine_name == "open_deep_research":
            try:
                from app.integrations.research_engine.open_deep_research.engine import OpenDeepResearchEngine
                logger.info("Instantiating OpenDeepResearchEngine")
                return OpenDeepResearchEngine(
                    llm_gateway=llm_gateway,
                    search_tool=search_tool,
                    redis_client=redis_client
                )
            except ImportError as e:
                logger.error(f"Failed to import OpenDeepResearchEngine: {e}, falling back to Legacy")
                return LegacyResearchEngine(
                    llm_gateway=llm_gateway,
                    search_tool=search_tool
                )
        else:
            logger.info("Instantiating LegacyResearchEngine")
            return LegacyResearchEngine(
                llm_gateway=llm_gateway,
                search_tool=search_tool
            )
