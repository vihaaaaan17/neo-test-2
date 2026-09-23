from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
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

# In-memory checkpointer safe for unit tests and local dev
if getattr(settings, "ASYNC_POSTGRES_SAVER_ENABLED", False):
    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        checkpointer = AsyncPostgresSaver.from_conn_string(settings.DATABASE_URL)
    except Exception:
        checkpointer = MemorySaver()
else:
    checkpointer = MemorySaver()

working_memory_engine = graph_builder.compile(checkpointer=checkpointer)
