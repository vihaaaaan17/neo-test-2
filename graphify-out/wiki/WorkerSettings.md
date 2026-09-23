# WorkerSettings

> 11 nodes · cohesion 0.18

## Key Concepts

- **WorkerSettings** (5 connections) — `workers/settings.py`
- **settings.py** (4 connections) — `workers/settings.py`
- **shutdown()** (2 connections) — `workers/settings.py`
- **startup()** (2 connections) — `workers/settings.py`
- **.get_queue_config()** (2 connections) — `workers/settings.py`
- **BaseWorkerSettings** (1 connections)
- **arq WorkerSettings — defines the worker process configuration. Run the worker…** (1 connections) — `workers/settings.py`
- **Returns the configuration for a specific queue.** (1 connections) — `workers/settings.py`
- **Runs once when the worker process starts. Populate shared resources.** (1 connections) — `workers/settings.py`
- **Runs once when the worker process shuts down.** (1 connections) — `workers/settings.py`
- **arq worker settings class. Discovered by: python -m arq…** (1 connections) — `workers/settings.py`

## Relationships

- [get_worker_pool_status](get_worker_pool_status.md) (1 shared connections)

## Source Files

- `workers/settings.py`

## Audit Trail

- EXTRACTED: 10 (91%)
- INFERRED: 1 (9%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*