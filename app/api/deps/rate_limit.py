from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request

def get_rate_limit_key(request: Request) -> str:
    """Rate limit by user ID if authenticated, else fallback to IP."""
    if hasattr(request.state, "user_id") and request.state.user_id:
        return str(request.state.user_id)
    return get_remote_address(request)

limiter = Limiter(key_func=get_rate_limit_key, default_limits=["60/minute"])
