import logging
from typing import Dict, Any, Optional
from uuid import UUID
from app.repositories.research import ResearchRepository
from app.core.config import settings
from app.integrations.research_engine.budget import UsageTracker

logger = logging.getLogger(__name__)

class ResearchBudgetPolicy:
    """
    Research-specific budget policy to enforce cost and usage limits.
    """

    def __init__(self, repository: ResearchRepository):
        self.repository = repository
        self.max_model_calls = settings.MAX_MODEL_CALLS
        self.max_input_tokens = settings.MAX_INPUT_TOKENS
        self.max_output_tokens = settings.MAX_OUTPUT_TOKENS
        self.max_cost = settings.MAX_COST

    async def check_budget(self, run_id: UUID, model_calls: int, input_tokens: int, output_tokens: int, cost: float) -> bool:
        """
        Check if the budget for a research run has been exceeded.
        Returns True if the budget has not been exceeded, False otherwise.
        """
        # Check model calls
        if model_calls > self.max_model_calls:
            return False

        # Check input tokens
        if input_tokens > self.max_input_tokens:
            return False

        # Check output tokens
        if output_tokens > self.max_output_tokens:
            return False

        # Check cost
        if cost > self.max_cost:
            return False

        return True

    def get_budget_status(self) -> Dict[str, Any]:
        """
        Returns the current budget status.
        """
        return {
            "max_model_calls": self.max_model_calls,
            "max_input_tokens": self.max_input_tokens,
            "max_output_tokens": self.max_output_tokens,
            "max_cost": self.max_cost
        }