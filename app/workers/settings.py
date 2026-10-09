"""
arq WorkerSettings — defines the worker process configuration.

Run the worker with:
    python -m arq app.workers.settings.WorkerSettings

The worker connects to Redis and processes jobs enqueued by the FastAPI API.
"""
from dotenv import load_dotenv
load_dotenv(".env")

import logging
from arq.connections import RedisSettings
from app.core.config import settings
from app.workers.tasks import (
    parse_and_chunk_job, compress_episodic_job, sync_knowledge_to_graph_job,
    run_research_agent_job, project_output_graph_job,
    export_workspace_job, project_to_open_notebook_job,
    process_deletion_tombstone_job, reconcile_deletion_tombstones_job
)
from arq.cron import cron

logger = logging.getLogger(__name__)


async def startup(ctx: dict) -> None:
    """Runs once when the worker process starts. Populate shared resources."""
    logger.info("NeosisLM worker starting up")

    # Validate checkpointer configuration (fail fast in production)
    from app.services.working_memory import validate_checkpointer
    validate_checkpointer()

    async def _real_llm_call(prompt: str, model: str = None, provider: str = None) -> str:
        # The configured provider decides key/base URL/model (resolve_llm_provider); the legacy
        # `model`/`provider` arguments are accepted for caller compatibility but not used.
        from app.core.config import resolve_llm_provider
        from langchain_openai import ChatOpenAI

        resolved = resolve_llm_provider(require_key=True)
        llm = ChatOpenAI(model=resolved.model, api_key=resolved.api_key, base_url=resolved.base_url)
        res = await llm.ainvoke(prompt)
        return res.content

    ctx["llm_call"] = _real_llm_call

    import aioboto3
    session = aioboto3.Session(
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION
    )
    s3_context = session.client("s3", endpoint_url=settings.S3_ENDPOINT_URL)
    ctx["s3_client"] = await s3_context.__aenter__()
    ctx["s3_context"] = s3_context


async def shutdown(ctx: dict) -> None:
    """Runs once when the worker process shuts down."""
    logger.info("NeosisLM worker shutting down")
    if "s3_context" in ctx:
        await ctx["s3_context"].__aexit__(None, None, None)


class WorkerSettings:
    """
arq worker settings class. Discovered by: python -m arq app.workers.settings.WorkerSettings
    """

    # Define logical queues for isolation
    QUEUES = {
        "research-high": {
            "functions": [run_research_agent_job],
            "max_jobs": 5,
            "queue_name": "research-high"
        },
        "research-standard": {
            "functions": [run_research_agent_job],
            "max_jobs": 20,
            "queue_name": "research-standard"
        },
        "ground-projection": {
            "functions": [project_output_graph_job, project_to_open_notebook_job],
            "max_jobs": 10,
            "queue_name": "ground-projection"
        },
        "source-processing": {
            "functions": [parse_and_chunk_job, compress_episodic_job],
            "max_jobs": 15,
            "queue_name": "source-processing"
        },
        "maintenance": {
            "functions": [reconcile_deletion_tombstones_job],
            "max_jobs": 3,
            "queue_name": "maintenance"
        }
    }

    functions = [
        run_research_agent_job,
        parse_and_chunk_job,
        compress_episodic_job,
        sync_knowledge_to_graph_job,
        project_output_graph_job,
        export_workspace_job,
        project_to_open_notebook_job,
        process_deletion_tombstone_job,
        reconcile_deletion_tombstones_job
    ]
    queue_name = "research-standard"
    max_jobs = 20
    cron_jobs = [
        cron(reconcile_deletion_tombstones_job, minute=set(range(0, 60, 5)))
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)

    # Retry policy: retry failed jobs up to 3 times with exponential backoff.
    # max_tries=1 here because tenacity handles retries *within* the job itself
    # for transient errors; arq retries handle process-level crashes.
    max_tries = 3
    job_timeout = 1800  # 30 minutes max per job for deep autonomous research

    def get_queue_config(self, queue_name):
        """
        Returns the configuration for a specific queue.
        """
        return self.QUEUES.get(queue_name, {})