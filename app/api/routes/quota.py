from fastapi import APIRouter, Depends, HTTPException, status, Query
from uuid import UUID
from typing import Dict, Any, Optional
from app.api.deps.auth import get_current_user
from app.core.database import get_db
from app.api.deps.arq import get_arq_redis
from app.repositories.research import ResearchRepository
from app.services.research.quota import ResearchQuotaService
from arq.connections import Redis
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

@router.get("/quota-status", response_model=Dict[str, Any])
async def get_quota_status(
    workspace_id: UUID = Query(...),
    current_user_id: UUID = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_arq_redis),
):
    """
    Get the current quota status for the user and workspace.
    """
    repository = ResearchRepository(session, redis_client)
    quota_service = ResearchQuotaService(repository)

    # Get the quota status
    quota_status = await quota_service.handle_quota_violation(current_user_id, workspace_id)

    return quota_status