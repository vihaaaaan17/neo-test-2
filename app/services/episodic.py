from typing import Callable, Awaitable
from uuid import UUID
import asyncio
import logging
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

from app.core.config import settings
from app.repositories.episodic import EpisodicRepository
from app.schemas.episodic import EpisodicMemoryCreate
from app.schemas.working_memory import WorkingMemoryState

logger = logging.getLogger(__name__)

# Global semaphore to limit concurrent LLM calls across all instances of the service
# in a single process.
llm_semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_LLM_CALLS)

class EpisodicMemoryService:
    def __init__(self, repository: EpisodicRepository, llm_gateway: Callable[[str], Awaitable[str]]):
        """
        llm_gateway: an async callable that takes a string prompt and returns a string summary.
        """
        self.repository = repository
        self.llm_gateway = llm_gateway

    async def compress_working_memory(
        self, 
        owner_id: UUID, 
        workspace_id: UUID, 
        working_state: WorkingMemoryState,
        run_id: UUID | None = None
    ):
        scratchpad_text = "\n".join(working_state.get("scratchpad", []))
        hypotheses_text = "\n".join(working_state.get("active_hypotheses", []))
        
        prompt = (
            "Summarize the following agent working memory into a dense semantic summary of decisions, "
            "failures, and key findings.\n\n"
            f"Scratchpad:\n{scratchpad_text}\n\n"
            f"Hypotheses:\n{hypotheses_text}"
        )
        
        # Wrapped call with backpressure, retry, and logging
        summary = await self._call_llm_with_backpressure(prompt, workspace_id)
        
        data = EpisodicMemoryCreate(
            event_type="working_memory_compression",
            summary=summary,
            run_id=run_id
        )
        return await self.repository.create_episode(
            owner_id=owner_id, 
            workspace_id=workspace_id, 
            data=data
        )

    async def enqueue_compression(
        self,
        arq_redis,
        owner_id: UUID,
        workspace_id: UUID,
        working_state: WorkingMemoryState,
        run_id: UUID | None = None
    ):
        """Dispatch compression to the background queue."""
        await arq_redis.enqueue_job(
            "compress_episodic_job",
            owner_id=str(owner_id),
            workspace_id=str(workspace_id),
            working_state=dict(working_state),
            run_id=str(run_id) if run_id else None
        )

    @retry(
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(Exception),
        reraise=True
    )
    async def _call_llm_with_backpressure(self, prompt: str, workspace_id: UUID) -> str:
        """Call LLM with concurrency limits and retries."""
        async with llm_semaphore:
            logger.info(f"LLM Call Started [Workspace: {workspace_id}] (Est. Tokens: {len(prompt) // 4})")
            try:
                response = await self.llm_gateway(prompt)
                logger.info(f"LLM Call Succeeded [Workspace: {workspace_id}] (Output Tokens: {len(response) // 4})")
                return response
            except Exception as e:
                logger.warning(f"LLM Call Failed [Workspace: {workspace_id}]: {e}")
                raise
