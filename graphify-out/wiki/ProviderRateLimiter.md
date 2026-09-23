# ProviderRateLimiter

> 19 nodes · cohesion 0.13

## Key Concepts

- **ProviderRateLimiter** (12 connections) — `services/research/rate_limiter.py`
- **ResearchAdmissionController** (10 connections) — `services/research/admission.py`
- **.__init__()** (4 connections) — `services/research/admission.py`
- **.check_rate_limit_status()** (4 connections) — `services/research/rate_limiter.py`
- **.get_queue_status()** (3 connections) — `services/research/admission.py`
- **research/rate_limiter.py** (3 connections) — `services/research/rate_limiter.py`
- **.enforce_rate_limit()** (3 connections) — `services/research/rate_limiter.py`
- **.get_rate_limit_status()** (3 connections) — `services/research/rate_limiter.py`
- **UUID** (3 connections)
- **.__init__()** (2 connections) — `services/research/rate_limiter.py`
- **Any** (2 connections)
- **Any** (1 connections)
- **Research Admission Controller to enforce quotas and rate limits before…** (1 connections) — `services/research/admission.py`
- **Returns the current queue status.** (1 connections) — `services/research/admission.py`
- **Redis** (1 connections)
- **Provider rate limiter to enforce rate limits on external providers. Uses Redis…** (1 connections) — `services/research/rate_limiter.py`
- **Enforces rate limits for a given provider type and identifier. Returns True if…** (1 connections) — `services/research/rate_limiter.py`
- **Checks the current rate limit status for a given provider type and identifier.…** (1 connections) — `services/research/rate_limiter.py`
- **Returns the current rate limit configuration.** (1 connections) — `services/research/rate_limiter.py`

## Relationships

- [create_research_run](create_research_run.md) (4 shared connections)
- [.admit_research_run](admit_research_run.md) (2 shared connections)
- [workspaces.py](workspaces.py.md) (2 shared connections)
- [ResearchRepository](ResearchRepository.md) (2 shared connections)
- [ResearchQuotaService](ResearchQuotaService.md) (1 shared connections)
- [FastAPI](FastAPI.md) (1 shared connections)
- [get_rate_limit_status](get_rate_limit_status.md) (1 shared connections)

## Source Files

- `services/research/admission.py`
- `services/research/rate_limiter.py`

## Audit Trail

- EXTRACTED: 26 (74%)
- INFERRED: 9 (26%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*