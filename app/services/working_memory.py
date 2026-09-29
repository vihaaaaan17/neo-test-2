import logging
from typing import Any, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from app.schemas.working_memory import WorkingMemoryState
from app.core.config import settings

logger = logging.getLogger(__name__)


def validate_checkpointer(env: Optional[str] = None) -> Any:
    """
    Validates checkpointer configuration on startup.
    In production, durable checkpointer is mandatory and fails fast if unavailable.
    In development or test, MemorySaver is permitted.
    """
    target_env = (env or getattr(settings, "NEOSIS_ENV", None) or getattr(settings, "ENVIRONMENT", "development")).lower()
    durable_enabled = getattr(settings, "ASYNC_POSTGRES_SAVER_ENABLED", False)

    if target_env == "production":
        if not durable_enabled:
            raise RuntimeError(
                "Production checkpointer requirement violated: AsyncPostgresSaver is unavailable. "
                "Production environment misconfiguration: ASYNC_POSTGRES_SAVER_ENABLED must be True. "
                "In-memory MemorySaver fallback is strictly prohibited in production."
            )
        try:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
            dsn = getattr(settings, "POSTGRES_DSN", None) or settings.DATABASE_URL
            return AsyncPostgresSaver.from_conn_string(dsn)
        except Exception as e:
            raise RuntimeError(
                f"Production checkpointer requirement violated: AsyncPostgresSaver is unavailable. "
                f"Production durable checkpointer failed to initialize: {e}. "
                "Refusing silent downgrade to ephemeral MemorySaver in production."
            ) from e
    else:
        if durable_enabled:
            try:
                from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
                dsn = getattr(settings, "POSTGRES_DSN", None) or settings.DATABASE_URL
                return AsyncPostgresSaver.from_conn_string(dsn)
            except Exception as e:
                logger.warning(
                    "AsyncPostgresSaver unavailable in %s environment (%s); falling back to MemorySaver.",
                    target_env, e
                )
                return MemorySaver()
        return MemorySaver()


validate_checkpointer_configuration = validate_checkpointer


def get_checkpointer() -> Any:
    """
    Returns the checkpointer instance appropriate for the current environment.
    """
    target_env = (getattr(settings, "NEOSIS_ENV", None) or getattr(settings, "ENVIRONMENT", "development")).lower()
    durable_enabled = getattr(settings, "ASYNC_POSTGRES_SAVER_ENABLED", False)

    if target_env == "production":
        return validate_checkpointer()

    if durable_enabled:
        try:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
            dsn = getattr(settings, "POSTGRES_DSN", None) or settings.DATABASE_URL
            return AsyncPostgresSaver.from_conn_string(dsn)
        except Exception as e:
            logger.warning("Falling back to MemorySaver in %s: %s", target_env, e)
            return MemorySaver()

    return MemorySaver()


def process_memory(state: WorkingMemoryState):
    # This is a passthrough node.
    # The LangGraph reducers (operator.add) will automatically
    # append any values passed into the graph execution. We return an empty dict
    # so we don't double-append the state.
    return {}


graph_builder = StateGraph(WorkingMemoryState)
graph_builder.add_node("process", process_memory)
graph_builder.add_edge(START, "process")
graph_builder.add_edge("process", END)

checkpointer = get_checkpointer()
working_memory_engine = graph_builder.compile(checkpointer=checkpointer)
