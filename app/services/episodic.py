from typing import Callable, Awaitable
from uuid import UUID
from app.repositories.episodic import EpisodicRepository
from app.schemas.episodic import EpisodicMemoryCreate
from app.schemas.working_memory import WorkingMemoryState

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
        
        summary = await self.llm_gateway(prompt)
        
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
