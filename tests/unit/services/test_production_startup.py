"""
tests/unit/services/test_production_startup.py

Unit tests for production startup hardening and fail-fast invariants:
- Fails fast on ephemeral MemorySaver in production.
- Fails fast on missing or default insecure JWT secret in production.
- Fails fast on unreachable PostgreSQL database in production.
- Fails fast on unreachable Redis instance in production.
- Permits MemorySaver and local developer defaults in development/test modes.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.core.config import settings
from app.core.startup import validate_production_startup


@pytest.mark.asyncio
async def test_production_fails_fast_on_ephemeral_checkpointer():
    """
    In production, MemorySaver fallback is strictly prohibited.
    Must fail fast with RuntimeError.
    """
    with patch.object(settings, "ENVIRONMENT", "production"), \
         patch.object(settings, "NEOSIS_ENV", "production"), \
         patch.object(settings, "ASYNC_POSTGRES_SAVER_ENABLED", False):
        with pytest.raises(RuntimeError) as exc_info:
            await validate_production_startup("production")
        assert "Production checkpointer requirement violated" in str(exc_info.value)
        assert "MemorySaver fallback is strictly prohibited in production" in str(exc_info.value)


@pytest.mark.asyncio
async def test_production_fails_fast_on_missing_or_default_secret():
    """
    In production, default development JWT secrets must fail fast.
    """
    with patch.object(settings, "ENVIRONMENT", "production"), \
         patch.object(settings, "NEOSIS_ENV", "production"), \
         patch.object(settings, "ASYNC_POSTGRES_SAVER_ENABLED", True), \
         patch.object(settings, "SUPABASE_JWT_SECRET", "super-secret-jwt-token-for-supabase-local-dev-only"), \
         patch("app.core.startup.validate_checkpointer"):
        with pytest.raises(RuntimeError) as exc_info:
            await validate_production_startup("production")
        assert "Insecure or default SUPABASE_JWT_SECRET detected" in str(exc_info.value)


@pytest.mark.asyncio
async def test_production_fails_fast_on_unreachable_infra():
    """
    In production, unreachable Database or Redis causes immediate fail-fast termination.
    """
    strong_secret = "a-very-secure-32-byte-production-secret-token"

    # 1. Database failure
    mock_fail_engine = MagicMock()
    mock_fail_engine.connect.return_value.__aenter__.side_effect = ConnectionRefusedError("Database offline")
    with patch.object(settings, "ENVIRONMENT", "production"), \
         patch.object(settings, "NEOSIS_ENV", "production"), \
         patch.object(settings, "ASYNC_POSTGRES_SAVER_ENABLED", True), \
         patch.object(settings, "SUPABASE_JWT_SECRET", strong_secret), \
         patch("app.core.startup.validate_checkpointer"), \
         patch("app.core.startup.engine", mock_fail_engine):
        with pytest.raises(RuntimeError) as exc_info:
            await validate_production_startup("production")
        assert "Database connection failed" in str(exc_info.value)

    # 2. Redis failure (Database succeeds)
    mock_ok_engine = MagicMock()
    mock_ok_engine.connect.return_value.__aenter__.return_value = AsyncMock()
    with patch.object(settings, "ENVIRONMENT", "production"), \
         patch.object(settings, "NEOSIS_ENV", "production"), \
         patch.object(settings, "ASYNC_POSTGRES_SAVER_ENABLED", True), \
         patch.object(settings, "SUPABASE_JWT_SECRET", strong_secret), \
         patch("app.core.startup.validate_checkpointer"), \
         patch("app.core.startup.engine", mock_ok_engine), \
         patch("redis.asyncio.from_url", side_effect=ConnectionRefusedError("Redis offline")):
        with pytest.raises(RuntimeError) as exc_info:
            await validate_production_startup("production")
        assert "Redis connection failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_dev_mode_permits_ephemeral_checkpointer():
    """
    In development or test mode, ephemeral MemorySaver and developer defaults are permitted.
    """
    with patch.object(settings, "ENVIRONMENT", "development"), \
         patch.object(settings, "NEOSIS_ENV", None), \
         patch.object(settings, "ASYNC_POSTGRES_SAVER_ENABLED", False):
        # Must execute cleanly without exception
        await validate_production_startup("development")


@pytest.mark.asyncio
async def test_successful_production_startup():
    """
    When all production invariants are met (durable checkpointer, strong secret, live DB, live Redis),
    startup completes successfully.
    """
    mock_ok_engine = MagicMock()
    mock_ok_engine.connect.return_value.__aenter__.return_value = AsyncMock()
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)

    with patch.object(settings, "ENVIRONMENT", "production"), \
         patch.object(settings, "NEOSIS_ENV", "production"), \
         patch.object(settings, "ASYNC_POSTGRES_SAVER_ENABLED", True), \
         patch.object(settings, "SUPABASE_JWT_SECRET", "super-strong-production-key-xyz-12345"), \
         patch("app.core.startup.validate_checkpointer"), \
         patch("app.core.startup.engine", mock_ok_engine), \
         patch("redis.asyncio.from_url", return_value=mock_redis):
        await validate_production_startup("production")
        mock_redis.ping.assert_awaited_once()
