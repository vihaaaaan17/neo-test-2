# Ticket 16: Tenant Quotas & LLM Backpressure

## User Story
As a platform operator, I want per-tenant resource limits and LLM call safeguards, so that one power user cannot consume all storage, create unlimited workspaces, or drain the entire LLM API budget.

## Scope
Build the `QuotaService`, enforce limits on all create paths, and add concurrency + retry controls to all LLM gateway calls.

## Tasks

### 1. QuotaService (`app/services/quota.py`)
Create a service that checks resource limits before any creation:
- `check_workspace_limit(owner_id)` — max 5 workspaces per user (free tier).
- `check_source_limit(workspace_id)` — max 50 sources per workspace.
- `check_storage_limit(workspace_id, new_bytes)` — max 500MB total per workspace.
- `check_knowledge_limit(workspace_id)` — max 1000 knowledge objects per workspace.
- Limits are configured via `Settings` (environment variables).

### 2. Enforce Quotas
- Inject `QuotaService` check before `WorkspaceRepository.create_workspace()`.
- Inject `QuotaService` check before source upload (in the upload endpoint or job).
- Inject `QuotaService` check before `KnowledgeRepository.create_knowledge()`.
- Return `HTTP 429 Too Many Requests` or `HTTP 403 Forbidden` with clear error message on quota breach.

### 3. LLM Backpressure (`app/services/episodic.py` + future LLM gateway)
- Add `asyncio.Semaphore(5)` to bound concurrent LLM calls.
- Wrap LLM gateway calls with `tenacity.retry` (3 attempts, exponential backoff 1-10s).
- Log token usage per call (input tokens, output tokens, model, workspace_id).

### 4. Quota Configuration
Add to `Settings`:
```python
MAX_WORKSPACES_PER_USER: int = 5
MAX_SOURCES_PER_WORKSPACE: int = 50
MAX_STORAGE_BYTES_PER_WORKSPACE: int = 500_000_000  # 500MB
MAX_KNOWLEDGE_PER_WORKSPACE: int = 1000
MAX_CONCURRENT_LLM_CALLS: int = 5
```

## Acceptance Criteria
- [ ] `QuotaService` created with all check methods.
- [ ] Workspace creation fails with clear error after exceeding limit.
- [ ] Source upload fails with clear error after exceeding limit.
- [ ] LLM calls are semaphore-bounded to 5 concurrent.
- [ ] LLM calls retry with exponential backoff on failure.
- [ ] Quota limits are configurable via environment.
- [ ] Tests verify quota enforcement.

## Estimated Effort
~2 hours
