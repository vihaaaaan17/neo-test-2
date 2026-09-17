# Ticket 14: Background Job Queue (arq + Redis)

## User Story
As a user, I want my document uploads to return immediately with a processing status, so that my browser doesn't time out and the platform remains responsive for everyone else.

## Scope
Introduce `arq` (async Redis queue) as the background job system. Move all long-running operations (parsing, chunking, episodic compression) out of the HTTP request path.

## Tasks

### 1. Add Redis to infrastructure
- Add Redis to `docker-compose.yml`.
- Add `REDIS_URL: str = "redis://localhost:6379"` to `Settings`.
- Add `arq` to `requirements.txt`.

### 2. Create job worker (`app/workers/`)
- Create `app/workers/__init__.py`.
- Create `app/workers/tasks.py` with job functions:
  - `parse_and_chunk_job(ctx, source_id, file_uri, workspace_id, owner_id)` — downloads from S3, runs Docling, chunks, and bulk-inserts to Postgres.
  - `compress_episodic_job(ctx, owner_id, workspace_id, working_state, run_id)` — calls the LLM gateway and stores the episode.
- All jobs MUST be idempotent (check if already processed before executing).

### 3. Create arq worker settings
- Create `app/workers/settings.py` with `WorkerSettings` class defining the Redis connection and registered functions.

### 4. Refactor upload endpoint
- Change the source upload API to:
  1. Upload file to S3.
  2. Create `Source` + `SourceSnapshot` with `status="pending"`.
  3. Enqueue `parse_and_chunk_job` via arq.
  4. Return `202 Accepted` with `{ "source_id": ..., "status": "pending" }`.

### 5. Add job status endpoint
- `GET /api/v1/sources/{source_id}/status` — returns current processing status.

## Acceptance Criteria
- [ ] Redis is running in docker-compose.
- [ ] `arq` is installed and worker starts successfully.
- [ ] Document upload returns `202 Accepted` immediately.
- [ ] Parsing + chunking happens in the background worker.
- [ ] Job status endpoint returns `pending`, `processing`, `completed`, or `failed`.
- [ ] Episodic compression can be dispatched as a background job.
- [ ] Jobs are idempotent.

## Estimated Effort
~3-4 hours
