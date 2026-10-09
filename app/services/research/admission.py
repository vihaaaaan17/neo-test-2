import logging
from typing import Optional, Dict, Any
from uuid import UUID
from fastapi import HTTPException, status
from app.repositories.research import ResearchRepository
from app.models.research import ResearchRun
from app.integrations.research_engine.engine import ROUTING_MODES, SUPPORTED_ENGINES
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
        engine: Optional[str] = None,
        engine_revision: Optional[str] = None,
        conversation_id: Optional[UUID] = None,
        turn_id: Optional[UUID] = None,
        base_commit_id: Optional[UUID] = None,
        timeline_epoch: Optional[int] = None,
        routing_mode: str = "explicit",
    ) -> ResearchRun:
        """
        Admits a new research run after checking quotas and rate limits.
        """
        # 0. Validate routing before any quota is consumed or any run is created. "auto" lets the EngineRouter pick
        #    (no engine name is stored up front); "explicit" requires a supported engine. "auto" is never an engine name.
        if routing_mode not in ROUTING_MODES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="unsupported_routing_mode"
            )
        if routing_mode == "auto" and engine is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="engine_not_allowed_with_auto_routing"
            )
        if routing_mode == "explicit" and engine not in SUPPORTED_ENGINES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="unsupported_research_engine"
            )

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
        # Every supported engine calls the LLM and search providers.
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
            routing_mode=routing_mode,
            engine_revision=engine_revision,
            conversation_id=conversation_id,
            turn_id=turn_id,
            base_commit_id=base_commit_id,
            timeline_epoch=timeline_epoch
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