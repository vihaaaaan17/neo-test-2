from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from typing import Dict, Any, Optional
from app.api.deps import get_current_user, get_db_session, get_arq_redis
from app.repositories.research import ResearchRepository
from app.models.research import ResearchRun
from app.integrations.research_engine.factory import ResearchEngineFactory
from app.services.research.lifecycle import ResearchLifecycleService
from app.services.research.admission import ResearchAdmissionController
from app.services.research.quota import ResearchQuotaService
from app.services.research.rate_limiter import ProviderRateLimiter
from app.core.config import settings
from arq.connections import Redis
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

@router.post("/workspaces/{workspace_id}/research", response_model=ResearchRun)
async def create_research_run(
    workspace_id: UUID,
    objective: str,
    engine: str = "open_deep_research",
    engine_revision: Optional[str] = None,
    current_user: Any = Depends(get_current_user),  # Using Any for simplicity; replace with actual User type
    session: AsyncSession = Depends(get_db_session),
    redis_client: Redis = Depends(get_arq_redis),
):
    """
    Create a new research run.
    """
    repository = ResearchRepository(session, redis_client)
    quota_service = ResearchQuotaService(repository)
    rate_limiter = ProviderRateLimiter(redis_client)
    admission_controller = ResearchAdmissionController(quota_service, rate_limiter, repository)
    lifecycle_service = ResearchLifecycleService(repository)

    # Admit the research run
    run = await admission_controller.admit_research_run(
        workspace_id=workspace_id,
        owner_id=current_user.id,
        objective=objective,
        engine=engine,
        engine_revision=engine_revision
    )

    # Transition to planning
    await lifecycle_service.transition_run(
        workspace_id=workspace_id,
        run_id=run.run_id,
        new_status="planning"
    )

    # Enqueue job
    job_id = await enqueue_research_job(
        workspace_id=workspace_id,
        run_id=run.run_id,
        engine=engine,
        engine_revision=engine_revision
    )

    return run

@router.get("/workspaces/{workspace_id}/research/queue-status", response_model=Dict[str, Any])
async def get_queue_status(
    workspace_id: UUID,
    current_user: Any = Depends(get_current_user),  # Using Any for simplicity; replace with actual User type
    session: AsyncSession = Depends(get_db_session),
    redis_client: Redis = Depends(get_arq_redis),
):
    """
    Get the current queue status.
    """
    repository = ResearchRepository(session, redis_client)
    quota_service = ResearchQuotaService(repository)
    rate_limiter = ProviderRateLimiter(redis_client)
    admission_controller = ResearchAdmissionController(quota_service, rate_limiter, repository)

    return await admission_controller.get_queue_status()

# Placeholder for enqueue_research_job function
async def enqueue_research_job(workspace_id: UUID, run_id: UUID, engine: str, engine_revision: Optional[str] = None):
    """
    Placeholder for enqueueing a research job.
    """
    return "job_id_placeholder"