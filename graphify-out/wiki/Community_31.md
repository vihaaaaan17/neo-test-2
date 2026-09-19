# Community 31

> 69 nodes · cohesion 0.05

## Key Concepts

- **tasks.py** (41 connections) — `app/workers/tasks.py`
- **ObjectStoreProtocol** (13 connections) — `app/services/storage.py`
- **workers/settings.py** (12 connections) — `app/workers/settings.py`
- **S3ObjectStore** (11 connections) — `app/services/storage.py`
- **storage.py** (10 connections) — `app/services/storage.py`
- **parse_and_chunk_job()** (10 connections) — `app/workers/tasks.py`
- **DocumentParser** (9 connections) — `app/services/parsing.py`
- **export_workspace_job()** (9 connections) — `app/workers/tasks.py`
- **get_object_store()** (8 connections) — `app/services/storage.py`
- **_get_source_and_snapshot()** (8 connections) — `app/workers/tasks.py`
- **compress_episodic_job()** (7 connections) — `app/workers/tasks.py`
- **run_research_agent_job()** (7 connections) — `app/workers/tasks.py`
- **sync_knowledge_to_graph_job()** (7 connections) — `app/workers/tasks.py`
- **BlockRepository** (6 connections) — `app/repositories/block.py`
- **project_output_graph_job()** (6 connections) — `app/workers/tasks.py`
- **Any** (6 connections)
- **test_parsing.py** (6 connections) — `tests/test_parsing.py`
- **test_tasks_export.py** (6 connections) — `tests/test_tasks_export.py`
- **parsing.py** (5 connections) — `app/services/parsing.py`
- **MockObjectStore** (5 connections) — `tests/test_parsing.py`
- **test_parse_document()** (5 connections) — `tests/test_parsing.py`
- **test_export_workspace_job_failure()** (4 connections) — `tests/test_tasks_export.py`
- **test_export_workspace_job_success()** (4 connections) — `tests/test_tasks_export.py`
- **.__init__()** (3 connections) — `app/services/export.py`
- **.parse_document()** (3 connections) — `app/services/parsing.py`
- *... and 44 more nodes in this community*

## Relationships

- [Community 34](Community_34.md) (24 shared connections)
- [Community 37](Community_37.md) (11 shared connections)
- [Community 195](Community_195.md) (6 shared connections)
- [Community 134](Community_134.md) (5 shared connections)
- [Community 43](Community_43.md) (4 shared connections)
- [Community 64](Community_64.md) (3 shared connections)
- [Community 15](Community_15.md) (1 shared connections)

## Source Files

- `app/repositories/block.py`
- `app/services/export.py`
- `app/services/parsing.py`
- `app/services/storage.py`
- `app/workers/settings.py`
- `app/workers/tasks.py`
- `tests/test_parsing.py`
- `tests/test_tasks_export.py`

## Audit Trail

- EXTRACTED: 154 (94%)
- INFERRED: 9 (6%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*