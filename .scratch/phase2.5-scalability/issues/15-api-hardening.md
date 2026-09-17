# Ticket 15: API Hardening (Rate Limits, CORS, Versioning, Lifecycle)

## User Story
As a platform operator, I want the API to defend itself against abuse, shut down gracefully, and support future frontend integration, so that one bad actor cannot take down the system for everyone.

## Scope
Add rate limiting, CORS, API versioning, graceful lifecycle management, deep health checks, and S3 connection pooling.

## Tasks

### 1. Rate Limiting (`slowapi`)
- Add `slowapi` to `requirements.txt`.
- Configure per-user rate limits:
  - General endpoints: 60 req/min.
  - Upload endpoints: 10 req/min, max file size 50MB.
- Rate limit key: user ID from JWT (fall back to IP for unauthenticated endpoints).

### 2. CORS Middleware
- Add `CORSMiddleware` to `main.py`.
- Configure `ALLOWED_ORIGINS` in `Settings` (default `["*"]` for dev, explicit list for prod).

### 3. API Versioning
- Prefix all existing routes with `/api/v1/`.
- Move health check to `/health` (unversioned) and `/api/v1/health` (versioned).

### 4. FastAPI Lifespan Handler
- Create `@asynccontextmanager async def lifespan(app)`:
  - **Startup**: Initialize S3 client (persistent, shared across requests). Store on `app.state`.
  - **Shutdown**: `await engine.dispose()`, flush OpenTelemetry, close S3 client.
- Refactor `S3ObjectStore` to accept a pre-initialized client instead of creating one per call.

### 5. Deep Health Check
- `/health` endpoint checks Postgres (`SELECT 1`), and returns `degraded` if any dependency is unreachable.

### 6. Multi-Worker Deployment
- Update `Dockerfile` to use `gunicorn` with `uvicorn.workers.UvicornWorker`.
- Default: `--workers 4`.
- Add dedicated `ThreadPoolExecutor(max_workers=2)` for Docling parsing.

## Acceptance Criteria
- [ ] Rate limiting active on all endpoints.
- [ ] CORS middleware configured.
- [ ] All routes prefixed with `/api/v1/`.
- [ ] FastAPI lifespan manages startup/shutdown.
- [ ] S3 client is created once and shared.
- [ ] Health check verifies Postgres connectivity.
- [ ] Dockerfile uses Gunicorn + multi-worker.
- [ ] Docling parsing uses dedicated thread pool.
- [ ] Existing tests still pass.

## Estimated Effort
~2-3 hours
