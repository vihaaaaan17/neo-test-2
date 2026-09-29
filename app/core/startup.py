import logging
from typing import Optional
from sqlalchemy import text
from app.core.config import settings
from app.core.database import engine
from app.services.working_memory import validate_checkpointer

logger = logging.getLogger(__name__)


async def validate_production_startup(env: Optional[str] = None):
    """
    Validates infrastructure, checkpointer, and security invariants during application startup.
    Fails fast with RuntimeError if any production invariant is violated.
    """
    target_env = (
        env
        or getattr(settings, "NEOSIS_ENV", None)
        or getattr(settings, "ENVIRONMENT", "development")
    ).lower()

    # 1. Checkpointer guard (validates AsyncPostgresSaver in production, permits MemorySaver in dev/test)
    validate_checkpointer(target_env)

    # 2. Production strict security and infrastructure checks
    if target_env == "production":
        logger.info("Executing production startup validation suite...")

        # A. Secrets & Configuration Invariants
        insecure_jwt_defaults = {
            "super-secret-jwt-token-for-supabase-local-dev-only",
            "mock-secret",
            "secret",
            "password",
            "",
        }
        jwt_secret = getattr(settings, "SUPABASE_JWT_SECRET", "")
        if not jwt_secret or jwt_secret.strip() in insecure_jwt_defaults:
            raise RuntimeError(
                "Production startup validation failed: Insecure or default SUPABASE_JWT_SECRET detected. "
                "Production environments must configure a strong, non-default JWT secret."
            )

        # B. Verify Database Connectivity
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("Production database connectivity verified.")
        except Exception as e:
            raise RuntimeError(
                f"Production startup validation failed: Database connection failed: {e}. "
                "Backend cannot start in production without verified database connectivity."
            ) from e

        # C. Verify Redis Connectivity
        try:
            import redis.asyncio as aioredis
            redis_client = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=3)
            await redis_client.ping()
            await redis_client.aclose()
            logger.info("Production Redis connectivity verified.")
        except Exception as e:
            raise RuntimeError(
                f"Production startup validation failed: Redis connection failed: {e}. "
                "Backend cannot start in production without verified Redis connectivity."
            ) from e

        logger.info("All production startup validation checks PASSED.")
    else:
        logger.info("Development/Testing startup mode active (%s); local fallbacks permitted.", target_env)
