# EpisodicRepository

> 31 nodes · cohesion 0.09

## Key Concepts

- **EpisodicRepository** (7 connections) — `repositories/episodic.py`
- **WorkingMemoryState** (7 connections) — `schemas/working_memory.py`
- **EpisodicMemoryService** (7 connections) — `services/episodic.py`
- **EpisodicMemory** (6 connections) — `models/episodic.py`
- **EpisodicMemoryCreate** (5 connections) — `schemas/episodic.py`
- **._call_llm_with_backpressure()** (5 connections) — `services/episodic.py`
- **.compress_working_memory()** (5 connections) — `services/episodic.py`
- **.create_episode()** (4 connections) — `repositories/episodic.py`
- **.get_episode_by_run_id()** (4 connections) — `repositories/episodic.py`
- **.enqueue_compression()** (4 connections) — `services/episodic.py`
- **UUID** (4 connections)
- **UUID** (3 connections)
- **.__init__()** (3 connections) — `services/episodic.py`
- **repositories/episodic.py** (2 connections) — `repositories/episodic.py`
- **.__init__()** (2 connections) — `repositories/episodic.py`
- **schemas/episodic.py** (2 connections) — `schemas/episodic.py`
- **EpisodicMemoryResponse** (2 connections) — `schemas/episodic.py`
- **services/episodic.py** (2 connections) — `services/episodic.py`
- **process_memory()** (2 connections) — `services/working_memory.py`
- **models/episodic.py** (1 connections) — `models/episodic.py`
- **Base** (1 connections)
- **AsyncSession** (1 connections)
- **Used by the background worker to detect duplicate compress_episodic_job calls.** (1 connections) — `repositories/episodic.py`
- **retry** (1 connections)
- **BaseModel** (1 connections)
- *... and 6 more nodes in this community*

## Relationships

- [tasks.py](tasks.py.md) (3 shared connections)
- [WorkspaceExportService](WorkspaceExportService.md) (1 shared connections)

## Source Files

- `models/episodic.py`
- `repositories/episodic.py`
- `schemas/episodic.py`
- `schemas/working_memory.py`
- `services/episodic.py`
- `services/working_memory.py`

## Audit Trail

- EXTRACTED: 38 (83%)
- INFERRED: 8 (17%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*