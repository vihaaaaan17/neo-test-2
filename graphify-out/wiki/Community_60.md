# Community 60

> 44 nodes · cohesion 0.08

## Key Concepts

- **test_ground_mode_api.py** (19 connections) — `tests/test_ground_mode_api.py`
- **GroundModeOrchestrator** (18 connections) — `app/orchestration/ground_mode.py`
- **HybridRetrievalService** (13 connections) — `app/services/hybrid_retrieval.py`
- **RetrievedChunk** (10 connections) — `app/services/hybrid_retrieval.py`
- **orchestration/ground_mode.py** (9 connections) — `app/orchestration/ground_mode.py`
- **hybrid_retrieval.py** (9 connections) — `app/services/hybrid_retrieval.py`
- **GroundModeState** (7 connections) — `app/orchestration/ground_mode.py`
- **deps/llm.py** (6 connections) — `app/api/deps/llm.py`
- **test_ground_mode.py** (6 connections) — `tests/test_ground_mode.py`
- **mock_gateways()** (6 connections) — `tests/test_ground_mode_api.py`
- **test_hybrid_retrieval.py** (6 connections) — `tests/test_hybrid_retrieval.py`
- **get_embed_gateway()** (5 connections) — `app/api/deps/llm.py`
- **get_llm_gateway()** (5 connections) — `app/api/deps/llm.py`
- **.__init__()** (5 connections) — `app/orchestration/ground_mode.py`
- **StateGraph** (5 connections)
- **get_hybrid_retrieval_service()** (4 connections) — `app/api/routes/workspaces.py`
- **.retrieve()** (4 connections) — `app/services/hybrid_retrieval.py`
- **test_ask_ground_mode_endpoint()** (4 connections) — `tests/test_ground_mode_api.py`
- **test_ground_mode_orchestrator_retry_on_hallucination()** (4 connections) — `tests/test_ground_mode.py`
- **test_ground_mode_orchestrator_success_first_try()** (4 connections) — `tests/test_ground_mode.py`
- **._build_graph()** (3 connections) — `app/orchestration/ground_mode.py`
- **.retrieve_node()** (3 connections) — `app/orchestration/ground_mode.py`
- **.run()** (3 connections) — `app/orchestration/ground_mode.py`
- **mock_arq_redis()** (3 connections) — `tests/test_ground_mode_api.py`
- **mock_current_user()** (3 connections) — `tests/test_ground_mode_api.py`
- *... and 19 more nodes in this community*

## Relationships

- [Community 43](Community_43.md) (9 shared connections)
- [Community 64](Community_64.md) (8 shared connections)
- [Community 34](Community_34.md) (6 shared connections)
- [Community 21](Community_21.md) (6 shared connections)
- [Community 37](Community_37.md) (5 shared connections)
- [Community 94](Community_94.md) (1 shared connections)
- [Community 77](Community_77.md) (1 shared connections)
- [Community 134](Community_134.md) (1 shared connections)
- [Community 202](Community_202.md) (1 shared connections)

## Source Files

- `app/api/deps/llm.py`
- `app/api/routes/workspaces.py`
- `app/orchestration/ground_mode.py`
- `app/services/hybrid_retrieval.py`
- `tests/test_ground_mode.py`
- `tests/test_ground_mode_api.py`
- `tests/test_hybrid_retrieval.py`

## Audit Trail

- EXTRACTED: 92 (79%)
- INFERRED: 25 (21%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*