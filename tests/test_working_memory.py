"""
Working memory tests.

The WorkingMemory engine uses AsyncPostgresSaver in production (multi-worker safe).
For unit tests we override the checkpointer back to MemorySaver so tests stay
hermetic and do not require a running Postgres instance.
"""
import pytest
from uuid import uuid4
from unittest.mock import patch
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END
from app.schemas.working_memory import WorkingMemoryState


def _build_test_engine():
    """Build a working memory engine with an in-process MemorySaver for tests."""
    def process_memory(state: WorkingMemoryState):
        return {}

    builder = StateGraph(WorkingMemoryState)
    builder.add_node("process", process_memory)
    builder.add_edge(START, "process")
    builder.add_edge("process", END)
    return builder.compile(checkpointer=MemorySaver())


def test_working_memory_accumulation():
    engine = _build_test_engine()

    thread_id = str(uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    # First update
    engine.invoke({
        "scratchpad": ["Found an interesting fact about X."],
        "pinned_evidence": [],
        "active_hypotheses": ["Hypothesis A"]
    }, config=config)

    # Second update
    evidence_id = uuid4()
    result = engine.invoke({
        "scratchpad": ["The fact is supported by evidence."],
        "pinned_evidence": [evidence_id],
        "active_hypotheses": []
    }, config=config)

    # Verify accumulation
    assert len(result["scratchpad"]) == 2
    assert "Found an interesting fact about X." in result["scratchpad"]
    assert "The fact is supported by evidence." in result["scratchpad"]

    assert len(result["pinned_evidence"]) == 1
    assert result["pinned_evidence"][0] == evidence_id

    assert len(result["active_hypotheses"]) == 1
    assert result["active_hypotheses"][0] == "Hypothesis A"


def test_working_memory_thread_isolation():
    """Different thread_ids must produce completely isolated state."""
    engine = _build_test_engine()

    thread1_id = str(uuid4())
    engine.invoke({
        "scratchpad": ["Thread 1 thought"],
        "pinned_evidence": [],
        "active_hypotheses": ["Thread 1 hypothesis"]
    }, config={"configurable": {"thread_id": thread1_id}})

    # A different thread starts fresh
    thread2_id = str(uuid4())
    result2 = engine.invoke({
        "scratchpad": ["A new thought"],
        "pinned_evidence": [],
        "active_hypotheses": []
    }, config={"configurable": {"thread_id": thread2_id}})

    assert len(result2["scratchpad"]) == 1
    assert len(result2["active_hypotheses"]) == 0
    assert "Thread 1 thought" not in result2["scratchpad"]
