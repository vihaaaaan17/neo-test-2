import logging
from typing import Any

from app.integrations.research_engine.engine import ResearchEngine, SUPPORTED_ENGINES
from app.integrations.research_engine.exceptions import ResearchEngineSetupError

logger = logging.getLogger(__name__)


class ResearchEngineFactory:
    """
    Resolves the research engine for a persisted ResearchRun.engine.

    Only engines in SUPPORTED_ENGINES can be instantiated. Admission rejects anything else
    before a run exists; this factory is the backstop. Configuration (ACTIVE_RESEARCH_ENGINE)
    never overrides an already persisted engine selection.
    """

    @staticmethod
    def get_engine(engine_name: str, redis_client: Any = None) -> ResearchEngine:
        if engine_name not in SUPPORTED_ENGINES:
            raise ResearchEngineSetupError(
                f"Unsupported research engine: {engine_name!r}. Supported engines: {', '.join(SUPPORTED_ENGINES)}"
            )

        if engine_name == "open_deep_research":
            try:
                from app.integrations.research_engine.open_deep_research.engine import OpenDeepResearchEngine
                logger.info("Instantiating OpenDeepResearchEngine")
                return OpenDeepResearchEngine(redis_client=redis_client)
            except ImportError as e:
                logger.error(f"Failed to import OpenDeepResearchEngine: {e}")
                raise ResearchEngineSetupError(f"Cannot load OpenDeepResearchEngine: {e}") from e

        if engine_name == "storm":
            try:
                from app.integrations.research_engine.storm.engine import StormResearchEngine
                logger.info("Instantiating StormResearchEngine")
                return StormResearchEngine(redis_client=redis_client)
            except ImportError as e:
                logger.error(f"Failed to import StormResearchEngine: {e}")
                raise ResearchEngineSetupError(f"Cannot load StormResearchEngine: {e}") from e

        if engine_name == "gpt_researcher":
            try:
                from app.integrations.research_engine.gpt_researcher.engine import GPTResearcherEngine
                logger.info("Instantiating GPTResearcherEngine")
                return GPTResearcherEngine(redis_client=redis_client)
            except ImportError as e:
                logger.error(f"Failed to import GPTResearcherEngine: {e}")
                raise ResearchEngineSetupError(f"Cannot load GPTResearcherEngine: {e}") from e

        # Unreachable while SUPPORTED_ENGINES only lists engines handled above.
        raise ResearchEngineSetupError(f"No adapter registered for engine: {engine_name!r}")
