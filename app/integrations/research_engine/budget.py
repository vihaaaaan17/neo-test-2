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

    def track_search_call(self):
        self.add_search_call()

    def track_error(self, error: str):
        if not hasattr(self, "errors"):
            self.errors = []
        self.errors.append(error)

    def get_usage_metrics(self) -> dict:
        return {
            "model_calls": self.model_calls,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "search_calls": self.search_calls,
            "retrieval_calls": self.retrieval_calls,
            "mcp_calls": self.mcp_calls,
        }
        
    def check_budget(self):
        if self.model_calls > self.max_model_calls:
            raise ResearchBudgetExceeded("Exceeded maximum model calls budget.")
        if self.input_tokens > self.max_input_tokens:
            raise ResearchBudgetExceeded("Exceeded maximum input tokens budget.")
        if self.output_tokens > self.max_output_tokens:
            raise ResearchBudgetExceeded("Exceeded maximum output tokens budget.")
        if self.search_calls > self.max_search_calls:
            raise ResearchBudgetExceeded("Exceeded maximum search calls budget.")

class ModelTimingHandler(AsyncCallbackHandler):
    """Measures wall time spent inside model calls (to tell model latency apart from search / orchestration time)."""

    def __init__(self):
        self._started: dict = {}
        self.calls = 0
        self.total_ms = 0.0
        self.max_ms = 0.0

    async def on_chat_model_start(self, serialized, messages, *, run_id, **kwargs) -> None:
        import time
        self._started[run_id] = time.monotonic()

    async def on_llm_start(self, serialized, prompts, *, run_id, **kwargs) -> None:
        import time
        self._started[run_id] = time.monotonic()

    async def on_llm_end(self, response: LLMResult, *, run_id, **kwargs) -> None:
        import time
        t0 = self._started.pop(run_id, None)
        if t0 is not None:
            ms = (time.monotonic() - t0) * 1000
            self.calls += 1
            self.total_ms += ms
            self.max_ms = max(self.max_ms, ms)

    async def on_llm_error(self, error, *, run_id, **kwargs) -> None:
        self._started.pop(run_id, None)

    def snapshot(self) -> dict:
        return {"model_calls_timed": self.calls, "model_time_ms": int(self.total_ms), "slowest_model_call_ms": int(self.max_ms)}


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
