import logging
import uuid
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timedelta
from redis.asyncio import Redis
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

class ProviderRateLimiter:
    """
    Provider rate limiter to enforce rate limits on external providers.
    Uses Redis for distributed rate limiting to prevent cross-worker 429 explosions.
    """

    def __init__(self, redis_client: Redis):
        self.redis_client = redis_client
        self.rate_limits = {
            "llm": {"limit": 10, "window_seconds": 60},
            "search": {"limit": 30, "window_seconds": 300},
            "mcp": {"limit": 5, "window_seconds": 60},
        }

    async def enforce_rate_limit(self, provider_type: str, identifier: UUID) -> bool:
        """
        Enforces rate limits for a given provider type and identifier.
        Returns True if the limit has not been exceeded, False otherwise.
        """
        key = f"rate_limit:{provider_type}:{identifier}"
        current_limit = self.rate_limits[provider_type]["limit"]
        window_seconds = self.rate_limits[provider_type]["window_seconds"]

        # Use Redis to track the number of calls in the current window
        now = datetime.now()
        start_of_window = now - timedelta(seconds=window_seconds)

        # Get all timestamps for calls in the current window
        timestamps = await self.redis_client.zrangebyscore(key, start_of_window.timestamp(), now.timestamp())

        # Remove timestamps older than the current window
        await self.redis_client.zremrangebyscore(key, 0, start_of_window.timestamp())

        if len(timestamps) >= current_limit:
            return False

        # Add unique member to prevent timestamp collision
        member = f"{now.timestamp()}:{uuid.uuid4()}"
        await self.redis_client.zadd(key, {member: now.timestamp()})
        # Set TTL to 2x the window so expired keys are automatically reclaimed by Redis
        await self.redis_client.expire(key, window_seconds * 2)
        return True

    async def check_rate_limit_status(self, provider_type: str, identifier: UUID) -> Dict[str, Any]:
        """
        Checks the current rate limit status for a given provider type and identifier.
        Returns a dictionary with the current status.
        """
        key = f"rate_limit:{provider_type}:{identifier}"
        current_limit = self.rate_limits[provider_type]["limit"]
        window_seconds = self.rate_limits[provider_type]["window_seconds"]

        now = datetime.now()
        start_of_window = now - timedelta(seconds=window_seconds)

        # Get all timestamps for calls in the current window
        timestamps = await self.redis_client.zrangebyscore(key, start_of_window.timestamp(), now.timestamp())

        return {
            "provider_type": provider_type,
            "identifier": str(identifier),
            "limit": current_limit,
            "window_seconds": window_seconds,
            "current_calls": len(timestamps),
            "limit_exceeded": len(timestamps) >= current_limit
        }

    async def get_rate_limit_status(self) -> Dict[str, Any]:
        """
        Returns the current rate limit configuration.
        """
        return {
            "llm": {
                "limit": self.rate_limits["llm"]["limit"],
                "window_seconds": self.rate_limits["llm"]["window_seconds"]
            },
            "search": {
                "limit": self.rate_limits["search"]["limit"],
                "window_seconds": self.rate_limits["search"]["window_seconds"]
            },
            "mcp": {
                "limit": self.rate_limits["mcp"]["limit"],
                "window_seconds": self.rate_limits["mcp"]["window_seconds"]
            }
        }