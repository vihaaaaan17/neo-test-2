import logging
from uuid import UUID

from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.outputs import LLMResult

logger = logging.getLogger(__name__)

class ResearchBudgetExceeded(Exception):
    """Raised when an execution exceeds its allocated budget."""
    pass

class UsageTracker:
    def __init__(self, 
                 max_model_calls: int = 100, 
                 max_input_tokens: int = 1_000_000, 
                 max_output_tokens: int = 200_000,
                 max_search_calls: int = 50):
        self.max_model_calls = max_model_calls
        self.max_input_tokens = max_input_tokens
        self.max_output_tokens = max_output_tokens
        self.max_search_calls = max_search_calls
        
        self.model_calls = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.search_calls = 0
        self.retrieval_calls = 0
        self.mcp_calls = 0
        
    def add_model_usage(self, input_tokens: int, output_tokens: int):
        self.model_calls += 1
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.check_budget()
        
    def add_search_call(self):
        self.search_calls += 1
        self.check_budget()
        
    def check_budget(self):
        if self.model_calls > self.max_model_calls:
            raise ResearchBudgetExceeded("Exceeded maximum model calls budget.")
        if self.input_tokens > self.max_input_tokens:
            raise ResearchBudgetExceeded("Exceeded maximum input tokens budget.")
        if self.output_tokens > self.max_output_tokens:
            raise ResearchBudgetExceeded("Exceeded maximum output tokens budget.")
        if self.search_calls > self.max_search_calls:
            raise ResearchBudgetExceeded("Exceeded maximum search calls budget.")

class BudgetEnforcingCallbackHandler(AsyncCallbackHandler):
    """Intercepts LLM results to track usage and enforce budgets."""
    
    def __init__(self, tracker: UsageTracker):
        self.tracker = tracker
        
    async def on_llm_end(self, response: LLMResult, **kwargs) -> None:
        """Track token usage after an LLM call completes."""
        if response.llm_output and "token_usage" in response.llm_output:
            usage = response.llm_output["token_usage"]
            self.tracker.add_model_usage(
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0)
            )
