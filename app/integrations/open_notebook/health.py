import logging
from app.integrations.open_notebook.config import is_open_notebook_enabled
from app.integrations.open_notebook.client import OpenNotebookClient

logger = logging.getLogger(__name__)

async def check_open_notebook_health() -> bool:
    """
    Check if the Open Notebook Ground Engine is reachable and healthy.
    
    Returns:
        True if the service is healthy or if the feature is disabled.
        False if the feature is enabled but the service is unreachable.
    """
    if not is_open_notebook_enabled():
        return True
        
    client = OpenNotebookClient()
    try:
        data = await client.get_health()
        return data.get("status") == "healthy"
    except Exception as e:
        logger.warning(f"Open Notebook health check failed: {e}")
        return False
