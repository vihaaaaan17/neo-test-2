# WorkspaceRepository

> 16 nodes · cohesion 0.27

## Key Concepts

- **WorkspaceRepository** (27 connections) — `repositories/workspace.py`
- **Workspace** (10 connections) — `models/workspace.py`
- **UUID** (8 connections)
- **WorkspaceCommit** (5 connections) — `models/workspace.py`
- **.get_workspace()** (5 connections) — `repositories/workspace.py`
- **.update_workspace()** (5 connections) — `repositories/workspace.py`
- **.delete_workspace()** (4 connections) — `repositories/workspace.py`
- **.create_commit()** (3 connections) — `repositories/workspace.py`
- **.create_workspace()** (3 connections) — `repositories/workspace.py`
- **.get_commit()** (3 connections) — `repositories/workspace.py`
- **.set_active_commit()** (3 connections) — `repositories/workspace.py`
- **models/workspace.py** (2 connections) — `models/workspace.py`
- **Base** (2 connections)
- **repositories/workspace.py** (2 connections) — `repositories/workspace.py`
- **.__init__()** (2 connections) — `repositories/workspace.py`
- **AsyncSession** (1 connections)

## Relationships

- [workspaces.py](workspaces.py.md) (11 shared connections)
- [OpenNotebookRepository](OpenNotebookRepository.md) (3 shared connections)
- [schemas/workspace.py](schemas-workspace.py.md) (2 shared connections)
- [WorkspaceExportService](WorkspaceExportService.md) (1 shared connections)
- [QuotaService](QuotaService.md) (1 shared connections)
- [run_research_agent_job](run_research_agent_job.md) (1 shared connections)
- [Source](Source.md) (1 shared connections)
- [upload_file_to_workspace](upload_file_to_workspace.md) (1 shared connections)

## Source Files

- `models/workspace.py`
- `repositories/workspace.py`

## Audit Trail

- EXTRACTED: 45 (85%)
- INFERRED: 8 (15%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*