# ResearchQuotaService

> God node · 19 connections · `services/research/quota.py`

**Community:** [ResearchQuotaService](ResearchQuotaService.md)

## Connections by Relation

### calls
- create_research_run() `INFERRED`
- get_queue_status() `INFERRED`
- start_research() `INFERRED`
- get_quota_status() `INFERRED`

### contains
- research/quota.py `EXTRACTED`

### method
- .handle_quota_violation() `EXTRACTED`
- .enforce_user_quota() `EXTRACTED`
- .enforce_workspace_quota() `EXTRACTED`
- .enforce_global_quota() `EXTRACTED`
- ._count_active_runs_by_owner() `EXTRACTED`
- ._count_active_runs_by_workspace() `EXTRACTED`
- .get_user_concurrency_status() `EXTRACTED`
- .get_workspace_concurrency_status() `EXTRACTED`
- .get_global_concurrency_status() `EXTRACTED`
- ._count_active_runs() `EXTRACTED`
- .__init__() `EXTRACTED`

### rationale_for
- Service to manage research quotas for users, workspaces, and globally. `EXTRACTED`

### references
- .__init__() `EXTRACTED`

### uses
- ResearchRun `INFERRED`

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*