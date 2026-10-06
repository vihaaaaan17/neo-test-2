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

    import os
    async def _real_llm_call(prompt: str, model: str = None, provider: str = None) -> str:
        provider_setting = (os.environ.get("LLM_PROVIDER") or provider or "openai").lower()
        if provider_setting == "nvidia" or (not os.environ.get("OPENAI_API_KEY") and os.environ.get("NVIDIA_API_KEY")):
            api_key = os.environ.get("NVIDIA_API_KEY") or os.environ.get("OPENAI_API_KEY")
            base_url = os.environ.get("NVIDIA_BASE_URL") or os.environ.get("NVIDIA_INVOKE_URL") or os.environ.get("OPENAI_BASE_URL") or "https://integrate.api.nvidia.com/v1"
            model_to_use = os.environ.get("NVIDIA_MODEL") or os.environ.get("OPENAI_MODEL") or "deepseek-ai/deepseek-v4.1-flash"
        else:
            api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("NVIDIA_API_KEY")
            base_url = os.environ.get("OPENAI_BASE_URL")
            model_to_use = os.environ.get("OPENAI_MODEL") or model or "gpt-4o"

        if api_key:
            from langchain_openai import ChatOpenAI
            if base_url and base_url.endswith("/chat/completions"):
                base_url = base_url.replace("/chat/completions", "")
            llm = ChatOpenAI(model=model_to_use, api_key=api_key, base_url=base_url)
            res = await llm.ainvoke(prompt)
            return res.content
        raise RuntimeError("Neither OPENAI_API_KEY nor NVIDIA_API_KEY is configured.")

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