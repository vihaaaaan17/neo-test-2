from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from app.schemas.working_memory import WorkingMemoryState
from app.core.config import settings

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

# AsyncPostgresSaver replaces the in-process MemorySaver.
# This is critical for multi-worker deployments:
#   - MemorySaver() stores state in a per-process Python dict.
#   - With multiple Gunicorn workers, two requests from the same user
#     hitting different workers would see different (diverged) state.
#   - AsyncPostgresSaver persists checkpoints to the canonical Postgres DB,
#     ensuring all workers share a single consistent state view.
checkpointer = AsyncPostgresSaver.from_conn_string(settings.DATABASE_URL)

working_memory_engine = graph_builder.compile(checkpointer=checkpointer)
