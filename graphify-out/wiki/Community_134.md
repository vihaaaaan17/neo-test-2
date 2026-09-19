# Community 134

> 22 nodes · cohesion 0.14

## Key Concepts

- **WorkingMemoryState** (12 connections) — `app/schemas/working_memory.py`
- **EpisodicMemoryService** (10 connections) — `app/services/episodic.py`
- **_build_test_engine()** (7 connections) — `tests/test_working_memory.py`
- **test_working_memory.py** (6 connections) — `tests/test_working_memory.py`
- **schemas/working_memory.py** (5 connections) — `app/schemas/working_memory.py`
- **._call_llm_with_backpressure()** (5 connections) — `app/services/episodic.py`
- **.compress_working_memory()** (5 connections) — `app/services/episodic.py`
- **.enqueue_compression()** (4 connections) — `app/services/episodic.py`
- **UUID** (4 connections)
- **services/working_memory.py** (4 connections) — `app/services/working_memory.py`
- **.__init__()** (3 connections) — `app/services/episodic.py`
- **process_memory()** (3 connections) — `app/services/working_memory.py`
- **test_working_memory_thread_isolation()** (3 connections) — `tests/test_working_memory.py`
- **test_working_memory_accumulation()** (2 connections) — `tests/test_working_memory.py`
- **TypedDict** (1 connections)
- **llm_gateway: an async callable that takes a string prompt and returns a string…** (1 connections) — `app/services/episodic.py`
- **Dispatch compression to the background queue.** (1 connections) — `app/services/episodic.py`
- **Call LLM with concurrency limits and retries.** (1 connections) — `app/services/episodic.py`
- **retry** (1 connections)
- **Working memory tests. The WorkingMemory engine uses AsyncPostgresSaver in…** (1 connections) — `tests/test_working_memory.py`
- **Build a working memory engine with an in-process MemorySaver for tests.** (1 connections) — `tests/test_working_memory.py`
- **Different thread_ids must produce completely isolated state.** (1 connections) — `tests/test_working_memory.py`

## Relationships

- [Community 34](Community_34.md) (9 shared connections)
- [Community 31](Community_31.md) (5 shared connections)
- [Community 60](Community_60.md) (1 shared connections)

## Source Files

- `app/schemas/working_memory.py`
- `app/services/episodic.py`
- `app/services/working_memory.py`
- `tests/test_working_memory.py`

## Audit Trail

- EXTRACTED: 43 (90%)
- INFERRED: 5 (10%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*