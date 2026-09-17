# 20: Ground Mode Orchestration (LangGraph)

**What to build:** The core reasoning engine for Ground Mode. Unlike the heavy autonomous loop, this is a simplified LangGraph state machine designed strictly to execute source-bounded Q&A using our hybrid retrieval pipeline.

**Blocked by:** 18

**Status:** ready-for-agent

- [ ] A new `GroundModeOrchestrator` is implemented (e.g. `app/orchestration/ground_mode.py`).
- [ ] It defines a LangGraph `StateGraph` with states conforming to our existing `WorkingMemory` contract.
- [ ] The graph implements a fast `Retrieve` node (calling `HybridRetrievalService`) and an `Answer` node.
- [ ] The graph explicitly checks that any generated answer does not rely on information outside the retrieved context (hallucination prevention).
- [ ] Unit/Integration tests verify that the orchestrator compiles and runs isolated test queries successfully.
