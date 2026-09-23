# FastAPI

> 10 nodes · cohesion 0.22

## Key Concepts

- **FastAPI** (19 connections)
- **arq.py** (5 connections) — `api/deps/arq.py`
- **get_arq_redis()** (3 connections) — `api/deps/arq.py`
- **get_rate_limit_key()** (3 connections) — `api/deps/rate_limit.py`
- **jobs.py** (3 connections) — `api/routes/jobs.py`
- **rate_limit.py** (2 connections) — `api/deps/rate_limit.py`
- **Request** (1 connections)
- **Dependency to get the arq Redis pool. We lazily initialize the pool and attach…** (1 connections) — `api/deps/arq.py`
- **Request** (1 connections)
- **Rate limit by user ID if authenticated, else fallback to IP.** (1 connections) — `api/deps/rate_limit.py`

## Relationships

- [workspaces.py](workspaces.py.md) (2 shared connections)
- [main.py](main.py.md) (2 shared connections)
- [run_research_agent_job](run_research_agent_job.md) (1 shared connections)
- [stream_job_events](stream_job_events.md) (1 shared connections)
- [auth.py](auth.py.md) (1 shared connections)
- [get_workspace_metrics](get_workspace_metrics.md) (1 shared connections)
- [ResearchQuotaService](ResearchQuotaService.md) (1 shared connections)
- [get_rate_limit_status](get_rate_limit_status.md) (1 shared connections)
- [create_research_run](create_research_run.md) (1 shared connections)
- [get_worker_pool_status](get_worker_pool_status.md) (1 shared connections)
- [OpenNotebookClient](OpenNotebookClient.md) (1 shared connections)
- [OpenNotebookRepository](OpenNotebookRepository.md) (1 shared connections)

## Source Files

- `api/deps/arq.py`
- `api/deps/rate_limit.py`
- `api/routes/jobs.py`

## Audit Trail

- EXTRACTED: 29 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*