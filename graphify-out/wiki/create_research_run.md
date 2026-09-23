# create_research_run

> 13 nodes · cohesion 0.24

## Key Concepts

- **create_research_run()** (13 connections) — `api/routes/research.py`
- **get_queue_status()** (11 connections) — `api/routes/research.py`
- **routes/research.py** (5 connections) — `api/routes/research.py`
- **enqueue_research_job()** (4 connections) — `api/routes/research.py`
- **UUID** (4 connections)
- **Any** (2 connections)
- **AsyncSession** (2 connections)
- **Redis** (2 connections)
- **get** (1 connections)
- **post** (1 connections)
- **Create a new research run.** (1 connections) — `api/routes/research.py`
- **Get the current queue status.** (1 connections) — `api/routes/research.py`
- **Placeholder for enqueueing a research job.** (1 connections) — `api/routes/research.py`

## Relationships

- [ProviderRateLimiter](ProviderRateLimiter.md) (4 shared connections)
- [ResearchRepository](ResearchRepository.md) (3 shared connections)
- [ResearchQuotaService](ResearchQuotaService.md) (2 shared connections)
- [FastAPI](FastAPI.md) (1 shared connections)

## Source Files

- `api/routes/research.py`

## Audit Trail

- EXTRACTED: 20 (69%)
- INFERRED: 9 (31%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*