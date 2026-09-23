# GroundModeOrchestrator

> 40 nodes · cohesion 0.07

## Key Concepts

- **GroundModeOrchestrator** (14 connections) — `orchestration/ground_mode.py`
- **HybridRetrievalService** (8 connections) — `services/hybrid_retrieval.py`
- **MemoryRouterService** (8 connections) — `services/memory_router.py`
- **GroundModeState** (7 connections) — `orchestration/ground_mode.py`
- **get_ground_engine()** (7 connections) — `services/ground/factory.py`
- **MemoryItem** (6 connections) — `schemas/context.py`
- **.__init__()** (5 connections) — `orchestration/ground_mode.py`
- **ContextBundle** (5 connections) — `schemas/context.py`
- **ground/factory.py** (5 connections) — `services/ground/factory.py`
- **.retrieve()** (4 connections) — `services/hybrid_retrieval.py`
- **orchestration/ground_mode.py** (3 connections) — `orchestration/ground_mode.py`
- **.retrieve_node()** (3 connections) — `orchestration/ground_mode.py`
- **.run()** (3 connections) — `orchestration/ground_mode.py`
- **.run()** (3 connections) — `services/ground/factory.py`
- **hybrid_retrieval.py** (3 connections) — `services/hybrid_retrieval.py`
- **RetrievedChunk** (3 connections) — `services/hybrid_retrieval.py`
- **.build_context()** (3 connections) — `services/memory_router.py`
- **get_hybrid_retrieval_service()** (2 connections) — `api/routes/workspaces.py`
- **.answer_node()** (2 connections) — `orchestration/ground_mode.py`
- **._build_graph()** (2 connections) — `orchestration/ground_mode.py`
- **.check_hallucination_node()** (2 connections) — `orchestration/ground_mode.py`
- **.hallucination_router()** (2 connections) — `orchestration/ground_mode.py`
- **UUID** (2 connections)
- **context.py** (2 connections) — `schemas/context.py`
- **BaseModel** (2 connections)
- *... and 15 more nodes in this community*

## Relationships

- [workspaces.py](workspaces.py.md) (4 shared connections)
- [ResearchModeOrchestrator](ResearchModeOrchestrator.md) (3 shared connections)
- [run_research_agent_job](run_research_agent_job.md) (2 shared connections)
- [FastAPI](FastAPI.md) (1 shared connections)
- [OpenNotebookRepository](OpenNotebookRepository.md) (1 shared connections)

## Source Files

- `api/routes/workspaces.py`
- `orchestration/ground_mode.py`
- `schemas/context.py`
- `services/ground/factory.py`
- `services/hybrid_retrieval.py`
- `services/memory_router.py`

## Audit Trail

- EXTRACTED: 54 (79%)
- INFERRED: 14 (21%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*