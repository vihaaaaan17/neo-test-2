# WorkspaceExportService

> 12 nodes · cohesion 0.21

## Key Concepts

- **WorkspaceExportService** (10 connections) — `services/export.py`
- **S3ObjectStore** (10 connections) — `services/storage.py`
- **export_workspace_job()** (5 connections) — `workers/tasks.py`
- **.__init__()** (3 connections) — `services/export.py`
- **export.py** (2 connections) — `services/export.py`
- **UUID** (2 connections)
- **.export_to_zip()** (2 connections) — `services/export.py`
- **AsyncSession** (1 connections)
- **.download_file()** (1 connections) — `services/storage.py`
- **.generate_presigned_url()** (1 connections) — `services/storage.py`
- **.__init__()** (1 connections) — `services/storage.py`
- **Background job: Executes the workspace export using WorkspaceExportService and…** (1 connections) — `workers/tasks.py`

## Relationships

- [ObjectStoreProtocol](ObjectStoreProtocol.md) (3 shared connections)
- [tasks.py](tasks.py.md) (3 shared connections)
- [WorkspaceRepository](WorkspaceRepository.md) (1 shared connections)
- [Source](Source.md) (1 shared connections)
- [run_research_agent_job](run_research_agent_job.md) (1 shared connections)
- [EpisodicRepository](EpisodicRepository.md) (1 shared connections)
- [DocumentBlock](DocumentBlock.md) (1 shared connections)

## Source Files

- `services/export.py`
- `services/storage.py`
- `workers/tasks.py`

## Audit Trail

- EXTRACTED: 16 (64%)
- INFERRED: 9 (36%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*