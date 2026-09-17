import logging
from arq import create_pool
from arq.connections import RedisSettings
from fastapi import Request
from app.core.config import settings

logger = logging.getLogger(__name__)

async def get_arq_redis(request: Request):
    """
    Dependency to get the arq Redis pool.
    We lazily initialize the pool and attach it to app.state
    so we don't create a new connection pool on every request.
    """
    if not hasattr(request.app.state, "arq_pool"):
        logger.info("Initializing arq Redis pool")
        redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
        request.app.state.arq_pool = await create_pool(redis_settings)
    
    return request.app.state.arq_pool
