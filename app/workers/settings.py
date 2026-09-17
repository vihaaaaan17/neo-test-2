"""
arq WorkerSettings — defines the worker process configuration.

Run the worker with:
    python -m arq app.workers.settings.WorkerSettings

The worker connects to Redis and processes jobs enqueued by the FastAPI API.
ctx["llm_call"] is populated in on_startup for use by compress_episodic_job.
"""
import logging
from arq.connections import RedisSettings
from app.core.config import settings
from app.workers.tasks import (
    parse_and_chunk_job, compress_episodic_job, sync_knowledge_to_graph_job,
    run_research_agent_job, project_output_graph_job
)

logger = logging.getLogger(__name__)


async def startup(ctx: dict) -> None:
    """Runs once when the worker process starts. Populate shared resources."""
    logger.info("NeosisLM worker starting up")
    # llm_call will be wired to LiteLLM in Phase 3.
    # For now it is None; compress_episodic_job raises a clear error if called
    # without it, which makes the missing dependency explicit rather than silent.
    ctx["llm_call"] = None


async def shutdown(ctx: dict) -> None:
    """Runs once when the worker process shuts down."""
    logger.info("NeosisLM worker shutting down")


class WorkerSettings:
    """arq worker settings class. Discovered by: python -m arq app.workers.settings.WorkerSettings"""

    functions = [
        parse_and_chunk_job, compress_episodic_job, sync_knowledge_to_graph_job,
        run_research_agent_job, project_output_graph_job
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)

    # Retry policy: retry failed jobs up to 3 times with exponential backoff.
    # max_tries=1 here because tenacity handles retries *within* the job itself
    # for transient errors; arq retries handle process-level crashes.
    max_tries = 3
    job_timeout = 300  # 5 minutes max per job
