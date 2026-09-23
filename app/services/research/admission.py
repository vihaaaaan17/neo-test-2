import logging
from typing import Optional, Dict, Any
from uuid import UUID
from fastapi import HTTPException, status
from app.repositories.research import ResearchRepository
from app.models.research import ResearchRun
from app.services.research.quota import ResearchQuotaService
from app.services.research.rate_limiter import ProviderRateLimiter

logger = logging.getLogger(__name__)

class ResearchAdmissionController:
    """
    Research Admission Controller to enforce quotas and rate limits before enqueuing jobs.
    """

    def __init__(
        self,
        quota_service: ResearchQuotaService,
        rate_limiter: ProviderRateLimiter,
        repository: ResearchRepository
    ):
        self.quota_service = quota_service
        self.rate_limiter = rate_limiter
        self.repository = repository

    async def admit_research_run(
        self,
        workspace_id: UUID,
        owner_id: UUID,
        objective: str,
        engine: str,
        engine_revision: Optional[str] = None
    ) -> ResearchRun:
        """
        Admits a new research run after checking quotas and rate limits.
        """
        # 1. Enforce user concurrency quota
        if await self.quota_service.enforce_user_quota(owner_id) == "QUOTA_EXCEEDED":
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="User research concurrency quota exceeded"
            )

        # 2. Enforce workspace concurrency quota
        if await self.quota_service.enforce_workspace_quota(workspace_id) == "QUOTA_EXCEEDED":
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Workspace research concurrency quota exceeded"
            )

        # 3. Enforce global concurrency quota
        if await self.quota_service.enforce_global_quota() == "QUOTA_EXCEEDED":
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Global research concurrency quota exceeded"
            )

        # 4. Enforce provider rate limits
        if engine == "open_deep_research":
            if not await self.rate_limiter.enforce_rate_limit("llm", owner_id):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="LLM provider rate limit exceeded"
                )
            if not await self.rate_limiter.enforce_rate_limit("search", workspace_id):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Search provider rate limit exceeded"
                )

        # 5. Create canonical ResearchRun
        return await self.repository.create_run(
            workspace_id=workspace_id,
            owner_id=owner_id,
            objective=objective,
            engine=engine,
            engine_revision=engine_revision
        )

    async def get_queue_status(self) -> Dict[str, Any]:
        """
        Returns the current queue status.
        """
        return {
            "user_limits": {"limit": self.quota_service.user_concurrency_limit},
            "workspace_limits": {"limit": self.quota_service.workspace_concurrency_limit},
            "global_limits": {"limit": self.quota_service.global_concurrency_limit},
            "rate_limits": await self.rate_limiter.get_rate_limit_status()
        }