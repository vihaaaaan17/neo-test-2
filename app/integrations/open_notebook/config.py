from app.core.config import settings
from urllib.parse import urlparse

def is_open_notebook_enabled() -> bool:
    """Check if the Open Notebook Ground Engine is enabled."""
    return settings.OPEN_NOTEBOOK_ENABLED

def get_open_notebook_base_url() -> str:
    """Get the base URL for the Open Notebook API."""
    return settings.OPEN_NOTEBOOK_BASE_URL.rstrip('/')

def get_open_notebook_timeout() -> int:
    """Get the default HTTP timeout for Open Notebook requests."""
    return settings.OPEN_NOTEBOOK_TIMEOUT
