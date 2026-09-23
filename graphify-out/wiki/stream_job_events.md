# stream_job_events

> 5 nodes · cohesion 0.40

## Key Concepts

- **stream_job_events()** (5 connections) — `api/routes/jobs.py`
- **ArqRedis** (1 connections)
- **get** (1 connections)
- **Request** (1 connections)
- **Streams Server-Sent Events (SSE) from the Redis Pub/Sub channel for a given job.** (1 connections) — `api/routes/jobs.py`

## Relationships

- [FastAPI](FastAPI.md) (1 shared connections)

## Source Files

- `api/routes/jobs.py`

## Audit Trail

- EXTRACTED: 5 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*