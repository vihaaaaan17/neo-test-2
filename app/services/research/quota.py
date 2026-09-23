import logging
from typing import Dict, Any, Optional
from uuid import UUID
from app.repositories.research import ResearchRepository
from app.core.config import settings

logger = logging.getLogger(__name__)

class ResearchQuotaService:
    """
    Service to manage research quotas for users, workspaces, and globally.
    """

    def __init__(self, repository: ResearchRepository):
        self.repository = repository
        self.user_concurrency_limit = settings.USER_CONCURRENCY_LIMIT
        self.workspace_concurrency_limit = settings.WORKSPACE_CONCURRENCY_LIMIT
        self.global_concurrency_limit = settings.GLOBAL_CONCURRENCY_LIMIT

    async def enforce_user_quota(self, owner_id: UUID) -> str:
        """
        Enforces the user concurrency quota.
        Returns ACCEPTED or QUOTA_EXCEEDED.
        """
        active_runs = await self._count_active_runs_by_owner(owner_id)
        if active_runs >= self.user_concurrency_limit:
            return "QUOTA_EXCEEDED"
        return "ACCEPTED"

    async def enforce_workspace_quota(self, workspace_id: UUID) -> str:
        """
        Enforces the workspace concurrency quota.
        Returns ACCEPTED or QUOTA_EXCEEDED.
        """
        active_runs = await self._count_active_runs_by_workspace(workspace_id)
        if active_runs >= self.workspace_concurrency_limit:
            return "QUOTA_EXCEEDED"
        return "ACCEPTED"

    async def enforce_global_quota(self) -> str:
        """
        Enforces the global concurrency limit.
        Returns ACCEPTED or QUOTA_EXCEEDED.
        """
        active_runs = await self._count_active_runs()
        if active_runs >= self.global_concurrency_limit:
            return "QUOTA_EXCEEDED"
        return "ACCEPTED"

    async def handle_quota_violation(self, owner_id: UUID, workspace_id: UUID) -> Dict[str, Any]:
        """
        Handles quota violations by providing details about the current quotas.
        Returns a dictionary with quota details.
        """
        user_quota = await self.enforce_user_quota(owner_id)
        workspace_quota = await self.enforce_workspace_quota(workspace_id)
        global_quota = await self.enforce_global_quota()

        return {
            "user_quota": user_quota,
            "workspace_quota": workspace_quota,
            "global_quota": global_quota,
            "user_concurrency_limit": self.user_concurrency_limit,
            "workspace_concurrency_limit": self.workspace_concurrency_limit,
            "global_concurrency_limit": self.global_concurrency_limit
        }

    async def _count_active_runs_by_owner(self, owner_id: UUID) -> int:
        """
        Count active research runs for a given owner.
        """
        from sqlalchemy import select, not_
        from app.models.research import ResearchRun

        stmt = select(ResearchRun).where(
            ResearchRun.owner_id == owner_id,
            ResearchRun.status.in_(["pending", "planning", "researching", "synthesizing", "finalizing"])
        )
        result = await self.repository.session.execute(stmt)
        return len(result.scalars().all())

    async def _count_active_runs_by_workspace(self, workspace_id: UUID) -> int:
        """
        Count active research runs for a given workspace.
        """
        from sqlalchemy import select, not_
        from app.models.research import ResearchRun

        stmt = select(ResearchRun).where(
            ResearchRun.workspace_id == workspace_id,
            ResearchRun.status.in_(["pending", "planning", "researching", "synthesizing", "finalizing"])
        )
        result = await self.repository.session.execute(stmt)
        return len(result.scalars().all())

    async def _count_active_runs(self) -> int:
        """
        Count all active research runs globally.
        """
        from sqlalchemy import select, not_
        from app.models.research import ResearchRun

        stmt = select(ResearchRun).where(
            ResearchRun.status.in_(["pending", "planning", "researching", "synthesizing", "finalizing"])
        )
        result = await self.repository.session.execute(stmt)
        return len(result.scalars().all())

    def get_user_concurrency_status(self) -> Dict[str, Any]:
        """
        Returns the current user concurrency status.
        """
        return {
            "limit": self.user_concurrency_limit,
            "status": "ACCEPTED"
        }

    def get_workspace_concurrency_status(self) -> Dict[str, Any]:
        """
        Returns the current workspace concurrency status.
        """
        return {
            "limit": self.workspace_concurrency_limit,
            "status": "ACCEPTED"
        }

    def get_global_concurrency_status(self) -> Dict[str, Any]:
        """
        Returns the current global concurrency status.
        """
        return {
            "limit": self.global_concurrency_limit,
            "status": "ACCEPTED"
        }