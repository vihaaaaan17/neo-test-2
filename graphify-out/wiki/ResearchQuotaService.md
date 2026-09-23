# ResearchQuotaService

> 33 nodes · cohesion 0.09

## Key Concepts

- **ResearchQuotaService** (19 connections) — `services/research/quota.py`
- **get_quota_status()** (8 connections) — `api/routes/quota.py`
- **.handle_quota_violation()** (7 connections) — `services/research/quota.py`
- **UUID** (6 connections)
- **.enforce_user_quota()** (5 connections) — `services/research/quota.py`
- **.enforce_workspace_quota()** (5 connections) — `services/research/quota.py`
- **Any** (4 connections)
- **._count_active_runs_by_owner()** (4 connections) — `services/research/quota.py`
- **._count_active_runs_by_workspace()** (4 connections) — `services/research/quota.py`
- **.enforce_global_quota()** (4 connections) — `services/research/quota.py`
- **routes/quota.py** (3 connections) — `api/routes/quota.py`
- **._count_active_runs()** (3 connections) — `services/research/quota.py`
- **.get_global_concurrency_status()** (3 connections) — `services/research/quota.py`
- **.get_user_concurrency_status()** (3 connections) — `services/research/quota.py`
- **.get_workspace_concurrency_status()** (3 connections) — `services/research/quota.py`
- **UUID** (2 connections)
- **research/quota.py** (2 connections) — `services/research/quota.py`
- **.__init__()** (2 connections) — `services/research/quota.py`
- **AsyncSession** (1 connections)
- **get** (1 connections)
- **Redis** (1 connections)
- **Get the current quota status for the user and workspace.** (1 connections) — `api/routes/quota.py`
- **Service to manage research quotas for users, workspaces, and globally.** (1 connections) — `services/research/quota.py`
- **Returns the current user concurrency status.** (1 connections) — `services/research/quota.py`
- **Returns the current workspace concurrency status.** (1 connections) — `services/research/quota.py`
- *... and 8 more nodes in this community*

## Relationships

- [ResearchRepository](ResearchRepository.md) (3 shared connections)
- [create_research_run](create_research_run.md) (2 shared connections)
- [FastAPI](FastAPI.md) (1 shared connections)
- [ProviderRateLimiter](ProviderRateLimiter.md) (1 shared connections)
- [workspaces.py](workspaces.py.md) (1 shared connections)

## Source Files

- `api/routes/quota.py`
- `services/research/quota.py`

## Audit Trail

- EXTRACTED: 49 (89%)
- INFERRED: 6 (11%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*