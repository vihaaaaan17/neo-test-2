# QuotaService

> 14 nodes · cohesion 0.21

## Key Concepts

- **QuotaService** (17 connections) — `services/quota.py`
- **UUID** (5 connections)
- **services/quota.py** (4 connections) — `services/quota.py`
- **get_quota_service()** (3 connections) — `services/quota.py`
- **.check_knowledge_limit()** (3 connections) — `services/quota.py`
- **.check_source_limit()** (3 connections) — `services/quota.py`
- **.check_storage_limit()** (3 connections) — `services/quota.py`
- **.check_workspace_limit()** (3 connections) — `services/quota.py`
- **AsyncSession** (2 connections)
- **.__init__()** (2 connections) — `services/quota.py`
- **Check if user has exceeded their workspace limit.** (1 connections) — `services/quota.py`
- **Check if workspace has exceeded its source count limit.** (1 connections) — `services/quota.py`
- **Check if workspace has exceeded its total storage limit.** (1 connections) — `services/quota.py`
- **Check if workspace has exceeded its knowledge memory limit.** (1 connections) — `services/quota.py`

## Relationships

- [workspaces.py](workspaces.py.md) (3 shared connections)
- [run_research_agent_job](run_research_agent_job.md) (3 shared connections)
- [Source](Source.md) (2 shared connections)
- [FastAPI](FastAPI.md) (1 shared connections)
- [upload_file_to_workspace](upload_file_to_workspace.md) (1 shared connections)
- [WorkspaceRepository](WorkspaceRepository.md) (1 shared connections)

## Source Files

- `services/quota.py`

## Audit Trail

- EXTRACTED: 22 (73%)
- INFERRED: 8 (27%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*