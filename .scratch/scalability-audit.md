# NeosisLM Scalability Audit — What Breaks at 100+ Concurrent Users

> **Purpose**: Exhaustive, line-by-line audit of every component built in Phase 1 and Phase 2 against the question: *"What happens when 100 simultaneous users hit this system on a free tier?"* This document does **not** modify `inital-plan.md`. It identifies every gap, proposes the fix, and rates severity.

---

## Table of Contents

1. [Database Connection Pool Exhaustion](#1-database-connection-pool-exhaustion)
2. [Single-Process Singleton Bottleneck](#2-single-process-singleton-bottleneck)
3. [No Background Job Queue](#3-no-background-job-queue)
4. [Working Memory is a Process-Local In-Memory Singleton](#4-working-memory-is-a-process-local-in-memory-singleton)
5. [S3 Client Created Per-Call](#5-s3-client-created-per-call)
6. [Docling Parsing Blocks the Worker Pool](#6-docling-parsing-blocks-the-worker-pool)
7. [No Rate Limiting or Request Throttling](#7-no-rate-limiting-or-request-throttling)
8. [No Response Caching](#8-no-response-caching)
9. [No Tenant-Level Resource Quotas](#9-no-tenant-level-resource-quotas)
10. [Missing Database Indexes on Hot Paths](#10-missing-database-indexes-on-hot-paths)
11. [Auth Dependency Decodes JWT on Every Request](#11-auth-dependency-decodes-jwt-on-every-request)
12. [No Health Check Depth](#12-no-health-check-depth)
13. [Episodic Compressor Has No Backpressure](#13-episodic-compressor-has-no-backpressure)
14. [Database Echo Mode Is On](#14-database-echo-mode-is-on)
15. [No Connection Recycling or Staleness Detection](#15-no-connection-recycling-or-staleness-detection)
16. [Missing Graceful Shutdown](#16-missing-graceful-shutdown)
17. [No CORS or API Versioning](#17-no-cors-or-api-versioning)
18. [Summary Matrix](#summary-matrix)

---

## 1. Database Connection Pool Exhaustion

**Severity**: 🔴 Critical

**What we have now**:
```python
# app/core/database.py
engine = create_async_engine(settings.DATABASE_URL, echo=True)
```

**What breaks**: SQLAlchemy's default async engine creates a pool of **5 connections** with a max overflow of **10**. That means at most **15 concurrent database operations** across the entire application. With 100 users, the 16th simultaneous request blocks until a connection is freed. Under sustained load, this cascades into `TimeoutError` exceptions and the entire API locks up.

**What to do**:
```python
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,                  # See item #14
    pool_size=20,                # Base pool connections
    max_overflow=30,             # Burst capacity (total = 50)
    pool_timeout=30,             # Seconds to wait before raising
    pool_recycle=1800,           # Recycle connections every 30min (prevents stale PG connections)
    pool_pre_ping=True,          # Detect dead connections before using them
)
```

**Why these numbers**: Supabase free tier PostgreSQL allows **60 direct connections**. We want `pool_size + max_overflow` to stay under that ceiling (leaving headroom for Alembic migrations, admin tools, etc). With 50 connections available, 100 users can sustain reasonable throughput because most API calls hold a connection for <50ms.

**Files affected**: [`database.py`](file:///d:/koding/codes/NeosisLM/app/core/database.py)

---

## 2. Single-Process Singleton Bottleneck

**Severity**: 🔴 Critical

**What we have now**: A single `uvicorn` process serving the entire FastAPI app. One Python process = one event loop = one GIL.

**What breaks**: Even though we use `async`, Python's GIL means CPU-bound work (Pydantic validation, JSON serialization, JWT decoding) serializes. At 100 concurrent users, the event loop saturates around **~200-500 requests/second** depending on payload complexity. Any synchronous call (like Docling parsing via `asyncio.to_thread`) eats a thread from the limited default thread pool (also small).

**What to do**:
1. **Run multiple Uvicorn workers**: `uvicorn app.main:app --workers 4` — each worker is a separate Python process with its own event loop. On a 2-core free-tier VM, 2-4 workers is optimal.
2. **Increase the default thread pool** for `asyncio.to_thread`: 
   ```python
   import asyncio
   from concurrent.futures import ThreadPoolExecutor
   
   loop = asyncio.get_event_loop()
   loop.set_default_executor(ThreadPoolExecutor(max_workers=8))
   ```
3. **Add Gunicorn as the process manager** (production): `gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker`

**Implication for Working Memory**: If we run multiple workers, the in-memory `MemorySaver` in `working_memory.py` becomes **per-process** — two requests from the same user hitting different workers won't see each other's state. See item #4.

**Files affected**: [`main.py`](file:///d:/koding/codes/NeosisLM/app/main.py), `Dockerfile`, deployment config

---

## 3. No Background Job Queue

**Severity**: 🔴 Critical

**What we have now**: Document parsing, chunking, and episodic compression all run **inline** with the HTTP request. When a user uploads a 200-page PDF:
1. The HTTP handler downloads from S3.
2. Calls `asyncio.to_thread(self._run_docling, temp_path)` — blocks a thread for potentially **30-120 seconds**.
3. Chunks the output and bulk-inserts to Postgres.
4. Only then returns a response.

**What breaks**: With 100 users uploading documents concurrently, we exhaust the thread pool immediately. The event loop backs up. Requests that have nothing to do with parsing (workspace CRUD, memory queries) start timing out because the entire process is saturated. The user's browser connection times out after 30-60 seconds anyway.

**What to do**:
1. **Introduce a job queue** — the `inital-plan.md` already specifies this (row 84: "Job Queue" → Redis + Celery/RQ). We need to implement it now, not later.
2. The upload endpoint should:
   - Accept the file and store it in S3 (**fast**, <2s).
   - Create a `Source` + `SourceSnapshot` record with `status=pending`.
   - Enqueue a background job: `parse_and_chunk(source_id)`.
   - Return `202 Accepted` with a job ID.
3. The user polls or subscribes (WebSocket/SSE) for completion.
4. **Free-tier recommendation**: Use Redis (free tier on Railway/Upstash) + `arq` (lightweight async job queue, much lighter than Celery).

**Files affected**: [`parsing.py`](file:///d:/koding/codes/NeosisLM/app/services/parsing.py), [`chunking.py`](file:///d:/koding/codes/NeosisLM/app/services/chunking.py), new `app/workers/` directory, [`config.py`](file:///d:/koding/codes/NeosisLM/app/core/config.py)

---

## 4. Working Memory is a Process-Local In-Memory Singleton

**Severity**: 🔴 Critical

**What we have now**:
```python
# app/services/working_memory.py
working_memory_engine = graph_builder.compile(checkpointer=MemorySaver())
```

`MemorySaver()` stores all checkpoints in a Python dictionary **inside the process**. This has three fatal problems at scale:

1. **Multi-worker amnesia**: With 4 Uvicorn workers, request A might hit worker 1 and request B (same user, same thread) hits worker 3. Worker 3 has no idea what worker 1 stored. The user's working memory appears to randomly forget things.
2. **Memory leak**: Every thread's entire state history lives in a dict. With 100 users each running multi-step research sessions, this dict grows unboundedly until the process OOMs and crashes.
3. **No persistence across restarts**: A deploy, a crash, or a worker recycle wipes everything.

**What to do**:
1. **Short-term (free tier)**: Switch to LangGraph's `AsyncPostgresSaver` — it uses our existing Postgres instance to persist checkpoints. Zero new infrastructure.
   ```python
   from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
   
   checkpointer = AsyncPostgresSaver.from_conn_string(settings.DATABASE_URL)
   working_memory_engine = graph_builder.compile(checkpointer=checkpointer)
   ```
2. **Medium-term (growth)**: Move to Redis-backed checkpointing for lower latency. LangGraph has `RedisSaver`.
3. **Long-term (scale)**: Dedicated workflow state service.

**Files affected**: [`working_memory.py`](file:///d:/koding/codes/NeosisLM/app/services/working_memory.py), [`config.py`](file:///d:/koding/codes/NeosisLM/app/core/config.py)

---

## 5. S3 Client Created Per-Call

**Severity**: 🟡 Medium

**What we have now**:
```python
# app/services/storage.py
async def upload_file(self, ...):
    async with self.session.client("s3", endpoint_url=self.endpoint_url) as s3_client:
        await s3_client.put_object(...)
```

Every upload and download creates a brand-new HTTP connection to S3, performs TLS handshake, authenticates, transfers, and tears down. With 100 users uploading or reading files concurrently, we're creating/destroying 100 TCP connections per second.

**What to do**:
1. Create the S3 client **once** during application startup (in a lifespan handler) and reuse it across requests.
2. Use `aioboto3`'s connection pooling properly:
   ```python
   @asynccontextmanager
   async def lifespan(app: FastAPI):
       app.state.s3_session = aioboto3.Session(...)
       async with app.state.s3_session.client("s3", ...) as client:
           app.state.s3_client = client
           yield
   ```

**Files affected**: [`storage.py`](file:///d:/koding/codes/NeosisLM/app/services/storage.py), [`main.py`](file:///d:/koding/codes/NeosisLM/app/main.py)

---

## 6. Docling Parsing Blocks the Worker Pool

**Severity**: 🟠 High

**What we have now**:
```python
# app/services/parsing.py
doc_dict = await asyncio.to_thread(self._run_docling, temp_path)
```

`asyncio.to_thread` delegates to the **default thread pool executor**, which has a default size of `min(32, os.cpu_count() + 4)`. On a 2-core VM, that's **6 threads**. If 6 users upload PDFs simultaneously, the 7th upload blocks until a thread frees. And Docling can take 30-120 seconds per document.

**What to do** (in addition to item #3's job queue):
1. **Dedicated parsing executor** with bounded concurrency:
   ```python
   parsing_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="docling")
   ```
   This ensures parsing never steals threads from other `to_thread` calls.
2. **Concurrency semaphore** to cap simultaneous parses:
   ```python
   parse_semaphore = asyncio.Semaphore(2)
   async def parse_document(self, ...):
       async with parse_semaphore:
           ...
   ```
3. Long-term: Move parsing to a separate worker process entirely (via the job queue).

**Files affected**: [`parsing.py`](file:///d:/koding/codes/NeosisLM/app/services/parsing.py)

---

## 7. No Rate Limiting or Request Throttling

**Severity**: 🟠 High

**What we have now**: Any authenticated user can send unlimited requests. A single malicious or buggy client can DDoS the entire platform by flooding the API.

**What to do**:
1. **Per-user rate limits** using `slowapi` (based on `limits`):
   ```python
   from slowapi import Limiter
   from slowapi.util import get_remote_address
   
   limiter = Limiter(key_func=get_remote_address)
   
   @app.get("/api/v1/workspaces")
   @limiter.limit("60/minute")
   async def list_workspaces(...):
   ```
2. **Tier-based limits**: Free-tier users get 60 req/min. Paid users get 600 req/min. Store limit tier in the JWT claims or a user table.
3. **Upload-specific limits**: Cap file size (e.g., 50MB free tier), cap concurrent uploads per user (e.g., 3), cap total storage per workspace.
4. **LLM call budget**: The `EpisodicMemoryService` calls an LLM. Each call costs money. Without limits, one user's runaway loop can drain your entire API credit budget.

**Files affected**: [`main.py`](file:///d:/koding/codes/NeosisLM/app/main.py), new middleware, [`config.py`](file:///d:/koding/codes/NeosisLM/app/core/config.py)

---

## 8. No Response Caching

**Severity**: 🟡 Medium

**What we have now**: Every identical request hits the database. If 50 users query the same workspace metadata within a minute, that's 50 identical Postgres round-trips.

**What to do**:
1. **In-process LRU cache** for hot, read-heavy paths (workspace metadata, source registry lookups):
   ```python
   from functools import lru_cache
   # or async-compatible: aiocache
   ```
2. **Redis cache layer** for shared cross-worker caching:
   - Cache workspace configs, source metadata, chunk lookups.
   - Use short TTLs (30-60s) so stale data risk is minimal.
   - Invalidate on writes.
3. **HTTP-level caching**: Add `Cache-Control` and `ETag` headers to read-only endpoints.

**Files affected**: [`workspace.py`](file:///d:/koding/codes/NeosisLM/app/repositories/workspace.py), new cache middleware

---

## 9. No Tenant-Level Resource Quotas

**Severity**: 🟠 High

**What we have now**: Any user can create unlimited workspaces, upload unlimited documents, and trigger unlimited parsing jobs. One power user can consume all available Postgres storage, all S3 storage, and all CPU capacity.

**What to do**:
1. **Workspace quotas**: Max workspaces per user (e.g., 5 for free tier).
2. **Storage quotas**: Track total bytes uploaded per workspace. Enforce limit before accepting upload.
3. **Document count limits**: Max sources per workspace (e.g., 50 for free tier).
4. **Knowledge memory limits**: Max knowledge objects per workspace.
5. **Implement a `QuotaService`** that checks limits before any create operation:
   ```python
   class QuotaService:
       async def check_workspace_limit(self, owner_id: UUID) -> bool:
           count = await self.repo.count_workspaces(owner_id)
           return count < settings.MAX_WORKSPACES_PER_USER
   ```

**Files affected**: New `app/services/quota.py`, all repository `create_*` methods

---

## 10. Missing Database Indexes on Hot Paths

**Severity**: 🟡 Medium

**What we have now**: We have an index on `knowledge_memories.owner_id` and `episodic_memories.owner_id`. But:
- `document_blocks` has no composite index on `(source_id, sequence)` — the exact query pattern used for chunk retrieval.
- `workspaces` has no index on `owner_id` — every `get_workspace` query does a sequential scan once the table grows past ~1000 rows.
- `source_snapshots` has no index on `source_id`.

**What breaks**: Without indexes, PostgreSQL does **full table scans**. This is the exact nightmare described in that tweet — "whole DB scan." At 100 users with 10,000+ rows per table, every query gets slower linearly. The database becomes the bottleneck.

**What to do**: Add composite indexes in a new Alembic migration:
```python
op.create_index('ix_document_blocks_source_sequence', 'document_blocks', ['source_id', 'sequence'])
op.create_index('ix_workspaces_owner_id', 'workspaces', ['owner_id'])
op.create_index('ix_source_snapshots_source_id', 'source_snapshots', ['source_id'])
op.create_index('ix_knowledge_memories_workspace_id', 'knowledge_memories', ['workspace_id'])
op.create_index('ix_episodic_memories_workspace_id', 'episodic_memories', ['workspace_id'])
```

**Files affected**: New Alembic migration

---

## 11. Auth Dependency Decodes JWT on Every Request

**Severity**: 🟢 Low (but compounds)

**What we have now**:
```python
# app/api/deps/auth.py
payload = jwt.decode(token, settings.SUPABASE_JWT_SECRET, algorithms=["HS256"], audience="authenticated")
```

JWT decoding is CPU-bound (HMAC verification). At 100 concurrent requests/second, this is ~100 HMAC-SHA256 operations per second per worker. This is negligible on its own but compounds with other CPU work.

**What to do**:
1. **Short-lived in-process token cache** keyed by token hash:
   ```python
   from cachetools import TTLCache
   _token_cache = TTLCache(maxsize=1000, ttl=60)
   ```
   Same token within 60 seconds returns cached `sub` without re-decoding.
2. Only beneficial under high load; harmless otherwise.

**Files affected**: [`auth.py`](file:///d:/koding/codes/NeosisLM/app/api/deps/auth.py)

---

## 12. No Health Check Depth

**Severity**: 🟢 Low

**What we have now**:
```python
@app.get("/health")
def health_check():
    return {"status": "ok"}
```

This always returns `ok` even if Postgres is down, S3 is unreachable, or Redis is dead. A load balancer will keep routing traffic to a broken instance.

**What to do**:
```python
@app.get("/health")
async def health_check():
    checks = {}
    try:
        async with async_session_maker() as session:
            await session.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception:
        checks["postgres"] = "error"
    # ... similar for S3, Redis
    status = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": status, "checks": checks}
```

**Files affected**: [`main.py`](file:///d:/koding/codes/NeosisLM/app/main.py)

---

## 13. Episodic Compressor Has No Backpressure

**Severity**: 🟠 High

**What we have now**: `EpisodicMemoryService.compress_working_memory()` calls `self.llm_gateway(prompt)` — an external LLM API call that can take **2-15 seconds** and costs real money. There is no:
- Concurrency limit on simultaneous LLM calls.
- Retry logic with exponential backoff.
- Circuit breaker if the LLM provider is down.
- Cost tracking or budget enforcement.

**What breaks**: 100 users finishing research runs simultaneously trigger 100 concurrent LLM API calls. The provider rate-limits you, the calls fail, and episodic memories are silently lost.

**What to do**:
1. **Semaphore-bounded concurrency**:
   ```python
   _llm_semaphore = asyncio.Semaphore(5)  # max 5 concurrent LLM calls
   
   async def compress_working_memory(self, ...):
       async with _llm_semaphore:
           summary = await self.llm_gateway(prompt)
   ```
2. **Retry with backoff** (use `tenacity`, already installed with langgraph):
   ```python
   from tenacity import retry, stop_after_attempt, wait_exponential
   
   @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
   async def _call_llm(self, prompt):
       return await self.llm_gateway(prompt)
   ```
3. **Move to job queue** for non-urgent compression (same queue as parsing).
4. **Budget tracker**: Log token usage per workspace, enforce monthly cap.

**Files affected**: [`episodic.py`](file:///d:/koding/codes/NeosisLM/app/services/episodic.py)

---

## 14. Database Echo Mode Is On

**Severity**: 🟡 Medium

**What we have now**:
```python
engine = create_async_engine(settings.DATABASE_URL, echo=True)
```

`echo=True` logs **every single SQL statement** to stdout. With 100 concurrent users, this generates enormous log volume, slows down I/O, and can actually degrade database performance by 10-20% due to the serialization overhead of formatting SQL strings.

**What to do**:
```python
engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG_SQL)
```
Add `DEBUG_SQL: bool = False` to `Settings`. Only enable in development.

**Files affected**: [`database.py`](file:///d:/koding/codes/NeosisLM/app/core/database.py), [`config.py`](file:///d:/koding/codes/NeosisLM/app/core/config.py)

---

## 15. No Connection Recycling or Staleness Detection

**Severity**: 🟡 Medium

**What we have now**: Default SQLAlchemy settings. Postgres connections that sit idle can be terminated by the server (Supabase free tier aggressively kills idle connections after ~60s). The application then tries to use a dead connection and gets `InterfaceError: connection is closed`.

**What to do**: Already addressed in item #1's `pool_pre_ping=True` and `pool_recycle=1800`, but worth calling out as its own concern. Under load, idle connections cycling in and out of the pool without health checks is a common source of mysterious 500 errors.

---

## 16. Missing Graceful Shutdown

**Severity**: 🟡 Medium

**What we have now**: No lifespan event handler. When the process shuts down (deploy, crash, scale-down), in-flight requests are killed mid-transaction, database connections are leaked, and background tasks are orphaned.

**What to do**:
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown: close DB pool, flush telemetry, drain job queue
    await engine.dispose()

app = FastAPI(title="NeosisLM API", lifespan=lifespan)
```

**Files affected**: [`main.py`](file:///d:/koding/codes/NeosisLM/app/main.py)

---

## 17. No CORS or API Versioning

**Severity**: 🟡 Medium

**What we have now**: No CORS middleware (the future frontend will be blocked by browser security). No API versioning (breaking changes will break all clients simultaneously).

**What to do**:
1. Add CORS middleware:
   ```python
   from fastapi.middleware.cors import CORSMiddleware
   app.add_middleware(CORSMiddleware, allow_origins=["*"], ...)
   ```
2. Version all routes under `/api/v1/`:
   ```python
   app.include_router(workspaces_router, prefix="/api/v1")
   ```

**Files affected**: [`main.py`](file:///d:/koding/codes/NeosisLM/app/main.py), all route files

---

## Summary Matrix

| # | Issue | Severity | Effort | When to Fix |
|---|-------|----------|--------|-------------|
| 1 | DB connection pool exhaustion | 🔴 Critical | 5 min | **Now** |
| 2 | Single-process singleton | 🔴 Critical | 15 min | **Now** |
| 3 | No background job queue | 🔴 Critical | 2-4 hrs | **Before Phase 3** |
| 4 | Working memory process-local | 🔴 Critical | 30 min | **Now** |
| 5 | S3 client per-call | 🟡 Medium | 20 min | Before Phase 3 |
| 6 | Docling blocks thread pool | 🟠 High | 20 min | Before Phase 3 |
| 7 | No rate limiting | 🟠 High | 1 hr | Before Phase 3 |
| 8 | No response caching | 🟡 Medium | 1-2 hrs | Phase 3 |
| 9 | No tenant quotas | 🟠 High | 2 hrs | Before Phase 3 |
| 10 | Missing DB indexes | 🟡 Medium | 15 min | **Now** |
| 11 | JWT decode per-request | 🟢 Low | 10 min | Phase 4+ |
| 12 | Shallow health check | 🟢 Low | 10 min | Before Phase 3 |
| 13 | Episodic compressor no backpressure | 🟠 High | 30 min | Before Phase 3 |
| 14 | DB echo mode on | 🟡 Medium | 2 min | **Now** |
| 15 | No connection recycling | 🟡 Medium | 5 min | **Now** |
| 16 | No graceful shutdown | 🟡 Medium | 15 min | Before Phase 3 |
| 17 | No CORS/API versioning | 🟡 Medium | 15 min | Before Phase 3 |

---

## Recommended Execution Order

**Immediate fixes (before writing another feature)**:
1. Fix DB pool settings (#1, #14, #15) — 10 minutes total
2. Switch `MemorySaver` to `AsyncPostgresSaver` (#4) — 30 minutes
3. Add missing indexes (#10) — 15 minutes
4. Multi-worker Uvicorn (#2) — 15 minutes

**Before Phase 3 starts**:
5. Background job queue with `arq` + Redis (#3, #6) — 2-4 hours
6. Rate limiting (#7) — 1 hour
7. Tenant quotas (#9) — 2 hours
8. LLM backpressure + retry (#13) — 30 minutes
9. Graceful shutdown + lifespan (#16) — 15 minutes
10. S3 client pooling (#5) — 20 minutes
11. CORS + API versioning (#17) — 15 minutes
12. Deep health check (#12) — 10 minutes

**Phase 3-4 timeframe**:
13. Response caching with Redis (#8)
14. JWT caching (#11)

---

> **Bottom line**: The tweet is right. The architecture decisions in `inital-plan.md` are solid — they already call for job queues, Redis caching, provider abstractions, and connection pooling. The gap is that we haven't wired those safeguards into the actual code yet. The 4 critical items (#1, #2, #3, #4) are the difference between "works on my machine" and "works for 100 users." Everything else is defense-in-depth.
