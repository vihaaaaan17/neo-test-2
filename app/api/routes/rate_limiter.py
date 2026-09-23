from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from typing import Dict, Any, Optional
from app.api.deps.auth import get_current_user
from app.api.deps.arq import get_arq_redis
from app.services.research.rate_limiter import ProviderRateLimiter
from arq.connections import Redis

router = APIRouter()

@router.get("/rate-limit-status", response_model=Dict[str, Any])
async def get_rate_limit_status(
    current_user_id: UUID = Depends(get_current_user),
    redis_client: Redis = Depends(get_arq_redis),
):
    """
    Get the current rate limit status for the user.
    """
    rate_limiter = ProviderRateLimiter(redis_client)

    llm_status = await rate_limiter.check_rate_limit_status("llm", current_user_id)
    search_status = await rate_limiter.check_rate_limit_status("search", current_user_id)

    return {
        "llm": llm_status,
        "search": search_status,
        "global_config": await rate_limiter.get_rate_limit_status()
    }