# NeosisLM — Chapter 3 Remediation: Fast-Track Consolidated Plan (2 Phases, 5 Tickets)
**Document Version:** 2.0.0 (Granular Engineering Edition)  
**Target Surface:** `app/`, `alembic/versions/`, `tests/`, `scripts/`  
**Source of Truth:** Consolidated from `.scratch/chapter-3-remediation/CHAPTER_3_GRANULAR_AUDIT_AND_REMEDIATION_PLAN.md` and `NEOSISLM_CHAPTER_2_3_REMEDIATION_DESIGN.md`  
**Purpose:** Provide an exhaustive, line-by-line, function-by-function execution plan so that no investigation time is lost. Every file, function, line number, bug, and exact code fix is specified below.

---

## Plan Architecture Overview

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ PHASE 1: Fabric, Execution & Schema Stabilization                                      │
│                                                                                        │
│   ├── Ticket 1: Core Fabric, Repository Repair & Consolidated DB Migration             │
│   │   ├── CC-01: Fix typing import on app/repositories/research.py:1                   │
│   │   ├── CC-05: Clean truncated block & restore create_usage() on research.py:287     │
│   │   ├── CC-08: Replace publish_json on research.py:342 with publish(json.dumps())    │
│   │   ├── Ticket 21: Fix batch_create_evidence return object in research.py:125        │
│   │   └── CC-03: Generate single Alembic migration for all 7 new columns               │
│   │                                                                                    │
│   ├── Ticket 2: Retriever Standardization, Tool Adapters & ACL Contracts               │
│   │   ├── CC-04: Re-export UsageTracker in app/services/research/budget.py             │
│   │   ├── Tickets 05-09: Standardize all retrievers to return List[ResearchSourceResult│
│   │   ├── Ticket 06: Implement normalize_evidence() on normalization.py:37             │
│   │   ├── Ticket 06: Pass workspace_id to create_evidence on neosis_search_tools.py:111│
│   │   ├── Ticket 09: Fix tuple loop & pass workspace_id on gpt_researcher_tool.py:52   │
│   │   ├── CC-10: Guard docling & langchain_mcp_adapters against ModuleNotFoundError    │
│   │   └── Ticket 10: Fail-closed STORM check in factory.py:38                          │
│   │                                                                                    │
│   └── Ticket 3: Durable Execution, Checkpointing & Lifecycle Resiliency                │
│       ├── CC-06 & Ticket 14: Remove run_id NameError from engine.py:39 & add fallback  │
│       ├── Ticket 14: Safe MemorySaver fallback in app/services/working_memory.py:2     │
│       ├── CC-07 & Ticket 15: Add datetime and ResearchMetricsService to lifecycle.py   │
│       └── Ticket 12: Align audit_claim_citations() in provenance.py:47                 │
└────────────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ PHASE 2: Governance, Scalability & Production Verification                             │
│                                                                                        │
│   ├── Ticket 4: Admission Control, Redis Rate Limiting & Worker Pool Isolation          │
│   │   ├── Ticket 17: Deduplicate admission.py and align quota/rate-limiter method names│
│   │   ├── Ticket 19: Add Redis TTL (expire) and UUID member keys in rate_limiter.py:47 │
│   │   ├── Ticket 18: Add 'finalizing' to active quota queries in quota.py:77           │
│   │   ├── Ticket 20: Fix WorkerSettings class-level functions and set queue names      │
│   │   ├── CC-11: Fix router auth dependencies and register in app/main.py              │
│   │   ├── Ticket 17: Wire admission_controller into workspaces.py:463                  │
│   │   └── Ticket 23: Open Notebook HTTP pool reuse & projection queue isolation        │
│   │                                                                                    │
│   └── Ticket 5: Test Suite Stabilization, Benchmarks & Final Verification               │
│       ├── CC-02 & Ticket 27: Fix // C++ comment syntax on test_rollback_verification.py│
│       ├── Ticket 26: Fix terminal state loop in test_failure_injection.py:65           │
│       ├── CC-09: Remove destructive sys.modules['langgraph'] pollution from test files │
│       ├── Tickets 24 & 25: Fix UUID parsing, session scope, and real cost in benchmarks│
│       └── Ticket 28: Restore Section 56 GATES.md & verify pytest 100% clean pass       │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

# PHASE 1: Fabric, Execution & Schema Stabilization

---

### Ticket 1: Core Fabric, Repository Repair & Consolidated DB Migration

#### 1.1 Fix Typing Imports in Repository
* **File:** `app/repositories/research.py`
* **Line:** 1–3
* **Bug / Error:** Missing `Dict, Any`. Causes `NameError: name 'Dict' is not defined` on line 94, crashing pytest collection project-wide.
* **Exact Code Fix:**
  ```python
  # Change:
  from typing import List, Optional
  # To:
  from typing import List, Optional, Dict, Any
  ```

#### 1.2 Fix Return Type in `batch_create_evidence`
* **File:** `app/repositories/research.py`
* **Function:** `batch_create_evidence()` (lines 90–128) and `_bulk_insert_evidence()` (lines 140–164)
* **Bug / Error:** Line 125 does `inserted_evidence.extend(batch)`, returning raw dictionaries (`List[dict]`) instead of `List[ResearchEvidence]`.
* **Exact Code Fix:**
  Modify `_bulk_insert_evidence` to return the created list of model instances, and extend `inserted_evidence` with those instances:
  ```python
  async def _bulk_insert_evidence(self, workspace_id: UUID, run_id: UUID, evidence_list: List[Dict[str, Any]]) -> List[ResearchEvidence]:
      evidence_objects = [
          ResearchEvidence(
              run_id=run_id,
              task_id=ev.get("task_id"),
              source_id=ev.get("source_id"),
              retriever=ev.get("retriever"),
              query=ev.get("query"),
              content=ev.get("content"),
              locator=ev.get("locator"),
              fingerprint=ev.get("fingerprint"),
              tags=ev.get("tags", []),
              provenance=ev.get("provenance"),
              source_resolution_status=ev.get("source_resolution_status", "unresolved_external"),
              provider=ev.get("provider"),
              provider_reference=ev.get("provider_reference")
          )
          for ev in evidence_list
      ]
      self.session.add_all(evidence_objects)
      await self.session.commit()
      return evidence_objects

  # In batch_create_evidence:
  for i in range(0, len(new_evidence), batch_size):
      batch = new_evidence[i:i + batch_size]
      created_batch = await self._bulk_insert_evidence(workspace_id, run_id, batch)
      inserted_evidence.extend(created_batch)
  ```

#### 1.3 Clean Truncated Methods in Repository & Restore `create_usage`
* **File:** `app/repositories/research.py`
* **Lines:** 267–315
* **Bug / Error:** Copy-paste left lines 291–308 as orphaned dead code starting with `await self._verify_run_workspace(run_id, workspace_id)\n usage = ResearchUsage...`. The signature of `create_usage` was deleted, which causes `OpenDeepResearchEngine.astream_events` line 116 (`await repo.create_usage(...)`) to crash on step 1 of every research run with `AttributeError`.
* **Exact Code Fix:**
  Replace lines 267–315 with clean implementations of both methods:
  ```python
  # ==========================
  # ResearchUsage
  # ==========================
  async def checkpoint_usage(self, workspace_id: UUID, run_id: UUID, usage_metrics: dict) -> ResearchUsage:
      """
      Persists usage metrics to the database as a periodic checkpoint.
      """
      await self._verify_run_workspace(run_id, workspace_id)
      usage = ResearchUsage(
          run_id=run_id,
          task_id=None,
          model_calls=usage_metrics.get('model_calls', 0),
          input_tokens=usage_metrics.get('input_tokens', 0),
          output_tokens=usage_metrics.get('output_tokens', 0),
          retrieval_calls=usage_metrics.get('retrieval_calls', 0),
          search_calls=usage_metrics.get('search_calls', 0),
          mcp_calls=usage_metrics.get('mcp_calls', 0),
          latency=usage_metrics.get('latency', 0.0),
          cost=usage_metrics.get('cost', 0.0),
          estimation_type="periodic_checkpoint"
      )
      self.session.add(usage)
      await self.session.commit()
      await self.session.refresh(usage)
      return usage

  async def create_usage(
      self,
      workspace_id: UUID,
      run_id: UUID,
      task_id: Optional[UUID] = None,
      model_calls: int = 0,
      input_tokens: int = 0,
      output_tokens: int = 0,
      retrieval_calls: int = 0,
      search_calls: int = 0,
      mcp_calls: int = 0,
      latency: float = 0.0,
      cost: float = 0.0,
      estimation_type: str = "exact"
  ) -> ResearchUsage:
      """
      Records a usage entry for a research run.
      """
      await self._verify_run_workspace(run_id, workspace_id)
      usage = ResearchUsage(
          run_id=run_id,
          task_id=task_id,
          model_calls=model_calls,
          input_tokens=input_tokens,
          output_tokens=output_tokens,
          retrieval_calls=retrieval_calls,
          search_calls=search_calls,
          mcp_calls=mcp_calls,
          latency=latency,
          cost=cost,
          estimation_type=estimation_type
      )
      self.session.add(usage)
      await self.session.commit()
      await self.session.refresh(usage)
      return usage
  ```

#### 1.4 Replace Non-Existent `publish_json` on Redis Client
* **File:** `app/repositories/research.py`
* **Function:** `create_event()` (lines 339–348)
* **Bug / Error:** Calls `await self.redis_client.publish_json(...)`. `publish_json` does not exist on `ArqRedis` or `redis.asyncio.Redis`, crashing with `AttributeError`.
* **Exact Code Fix:**
  ```python
  import json
  # In create_event:
  if self.redis_client:
      channel = f"research_events:{run_id}"
      await self.redis_client.publish(
          channel,
          json.dumps({
              "run_id": str(run_id),
              "event_type": event_type,
              "sequence": next_sequence,
              "payload": payload
          })
      )
  ```

#### 1.5 Consolidated Alembic Migration for All 7 Model Columns
* **File:** `alembic/versions/7da81234abcd_add_ch3_remediation_columns.py` (New file)
* **Down Revision:** `89b7da012555`
* **Bug / Error:** `app/models/research.py` added 7 columns without a database migration. Any SQL execution against real PostgreSQL crashes with `UndefinedColumnError`.
* **Exact Code Fix:**
  Create migration with:
  ```python
  """Add Chapter 3 remediation columns

  Revision ID: 7da81234abcd
  Revises: 89b7da012555
  Create Date: 2026-09-22
  """
  from alembic import op
  import sqlalchemy as sa
  from sqlalchemy.dialects import postgresql

  revision = '7da81234abcd'
  down_revision = '89b7da012555'
  branch_labels = None
  depends_on = None

  def upgrade() -> None:
      # research_runs
      op.add_column('research_runs', sa.Column('current_attempt_id', sa.UUID(), nullable=True))
      
      # research_evidence
      op.add_column('research_evidence', sa.Column('source_resolution_status', sa.String(), server_default='unresolved_external', nullable=False))
      op.add_column('research_evidence', sa.Column('provider', sa.String(), nullable=True))
      op.add_column('research_evidence', sa.Column('provider_reference', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
      
      # research_reports
      op.add_column('research_reports', sa.Column('provenance_version', sa.String(), server_default='v1', nullable=False))
      op.add_column('research_reports', sa.Column('status', sa.String(), server_default='draft', nullable=False))
      
      # research_events
      op.add_column('research_events', sa.Column('sequence', sa.Integer(), server_default='1', nullable=False))

  def downgrade() -> None:
      op.drop_column('research_events', 'sequence')
      op.drop_column('research_reports', 'status')
      op.drop_column('research_reports', 'provenance_version')
      op.drop_column('research_evidence', 'provider_reference')
      op.drop_column('research_evidence', 'provider')
      op.drop_column('research_evidence', 'source_resolution_status')
      op.drop_column('research_runs', 'current_attempt_id')
  ```

---

### Ticket 2: Retriever Standardization, Tool Adapters & ACL Contracts

#### 2.1 Re-Export `UsageTracker` in Budget Module
* **File:** `app/services/research/budget.py`
* **Line:** 1–8
* **Bug / Error:** All 4 retrievers import `from app.services.research.budget import UsageTracker`. It is not defined there, raising `ImportError`.
* **Exact Code Fix:**
  Add the re-export to `app/services/research/budget.py`:
  ```python
  from app.integrations.research_engine.budget import UsageTracker
  ```

#### 2.2 Standardize Concrete Retrievers to Return `List[ResearchSourceResult]`
* **Files:**
  * `app/services/research/retrievers/web.py`
  * `app/services/research/retrievers/academic.py`
  * `app/services/research/retrievers/mcp.py`
  * `app/services/research/retrievers/gpt_researcher.py`
* **Bug / Error:** All return a 2-tuple `(source_results, self.usage_tracker.get_usage_metrics())` on success, but `[]` on error. Any caller iterating the return value crashes.
* **Exact Code Fix:**
  * In `web.py:79`: Change `return source_results, self.usage_tracker.get_usage_metrics()` to `return source_results`.
  * In `academic.py:90`: Change `return source_results, self.usage_tracker.get_usage_metrics()` to `return source_results`.
  * In `mcp.py:83, 88`: Change return to `return results` (and `return []` on error).
  * In `gpt_researcher.py:96, 101`: Change return to `return research_source_results` (and `return []` on error).
  * In `registry.py:77–78`: `retrieve()` now cleanly receives and returns `List[ResearchSourceResult]`.

#### 2.3 Implement `normalize_evidence` on Normalization Service
* **File:** `app/services/research/normalization.py`
* **Function:** `ResearchNormalizationService` (add method)
* **Bug / Error:** `neosis_search_tools.py:97` calls `normalizer.normalize_evidence(content=..., locator=...)`. Raises `AttributeError`.
* **Exact Code Fix:**
  Add method to `ResearchNormalizationService`:
  ```python
  def normalize_evidence(self, content: str, locator: str, retriever: str = None, query: str = None) -> str:
      """
      Normalizes evidence and computes a deduplicating SHA-256 fingerprint.
      """
      normalized_url = self.normalize_url(locator) if locator else None
      return self.generate_fingerprint(content=content, url=normalized_url)
  ```

#### 2.4 Fix `create_evidence` Callers in Tools
* **Files:**
  * `app/integrations/research_engine/tools/neosis_search_tools.py` (line 111)
  * `app/integrations/research_engine/tools/gpt_researcher_tool.py` (line 54)
* **Bug / Error:** Both tools call `await repo.create_evidence(...)` with keyword arguments but omit the required positional parameter `workspace_id`, raising `TypeError`. Furthermore, `gpt_researcher_tool.py:52` assumed a tuple return.
* **Exact Code Fix:**
  * In `neosis_search_tools.py:111`:
    ```python
    await repo.create_evidence(
        workspace_id=workspace_id,
        run_id=run_id,
        task_id=None,
        source_id=None,
        retriever="tavily_web_search",
        query=query,
        content=raw_content,
        locator=url,
        fingerprint=fingerprint,
        tags=["search_result"],
        provenance={"title": title, "url": url},
        source_resolution_status="unresolved_external",
        provider="tavily",
        provider_reference={"raw_score": result.get("score")}
    )
    ```
  * In `gpt_researcher_tool.py:52–68`:
    ```python
    results = await self.retriever.retrieve(query=query, report_type=report_type)
    for result in results:
        await repo.create_evidence(
            workspace_id=workspace_id,
            run_id=run_id,
            task_id=None,
            source_id=None,
            retriever=result.retriever,
            query=result.query,
            content=result.content,
            locator=result.url,
            fingerprint=result.provenance.get("fingerprint"),
            tags=["gpt_researcher_result"],
            provenance=result.provenance,
            source_resolution_status=result.source_resolution_status,
            provider=result.provider,
            provider_reference=result.provider_reference
        )
    ```

#### 2.5 Guard Optional Upstream Dependencies
* **Files:**
  * `app/integrations/research_engine/upstream/open_deep_research/utils.py` (line 27)
  * `app/services/parsing.py` (line 5)
* **Bug / Error:** Top-level imports of uninstalled packages `langchain_mcp_adapters` and `docling` crash on startup.
* **Exact Code Fix:**
  * In `utils.py:27`:
    ```python
    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
    except ImportError:
        MultiServerMCPClient = None
    ```
  * In `app/services/parsing.py:5`:
    ```python
    try:
        from docling.document_converter import DocumentConverter
    except ImportError:
        DocumentConverter = None
    ```

#### 2.6 Fail-Closed STORM Check in Factory
* **File:** `app/integrations/research_engine/factory.py`
* **Function:** `ResearchEngineFactory.get_engine()` (lines 38–56)
* **Bug / Error:** Requesting `engine_name="storm"` silently creates `LegacyResearchEngine`.
* **Exact Code Fix:**
  ```python
  if engine_name == "open_deep_research":
      ...
  elif engine_name == "storm":
      if not settings.STORM_ENABLED:
          raise ResearchEngineSetupError(
              "STORM engine is formally deferred to Chapter 5 and currently disabled (STORM_ENABLED=False)."
          )
      raise ResearchEngineSetupError("STORM engine runtime is not yet registered.")
  elif engine_name == "legacy":
      logger.info("Instantiating LegacyResearchEngine")
      return LegacyResearchEngine(llm_gateway=llm_gateway, search_tool=search_tool)
  else:
      raise ResearchEngineSetupError(f"Unknown research engine: {engine_name}")
  ```

---

### Ticket 3: Durable Execution, Checkpointing & Lifecycle Resiliency

#### 3.1 Fix `OpenDeepResearchEngine` Checkpointer & NameError
* **File:** `app/integrations/research_engine/open_deep_research/engine.py`
* **Lines:** 35–43
* **Bug / Error:** Line 39 passes `thread_id=str(run_id)` inside `__init__`, where `run_id` is undefined (`NameError`). Also package `langgraph-checkpoint-postgres` is not installed.
* **Exact Code Fix:**
  ```python
  from langgraph.checkpoint.memory import MemorySaver

  # Use AsyncPostgresSaver for production if available, MemorySaver for dev
  if settings.ASYNC_POSTGRES_SAVER_ENABLED:
      try:
          from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
          # Thread ID is passed per-execution in config, never in checkpointer constructor
          self.checkpointer = AsyncPostgresSaver.from_conn_string(settings.POSTGRES_DSN)
      except Exception as e:
          logger.warning(f"AsyncPostgresSaver unavailable ({e}); falling back to MemorySaver")
          self.checkpointer = MemorySaver()
  else:
      self.checkpointer = MemorySaver()

  self.graph = deep_researcher_builder.compile(checkpointer=self.checkpointer)
  ```

#### 3.2 Safe Checkpointer in Working Memory
* **File:** `app/services/working_memory.py`
* **Lines:** 1–28
* **Bug / Error:** Top-level import of `langgraph.checkpoint.postgres.aio` crashes when package is absent. Synchronous `from_conn_string` call at import time fails outside an async loop.
* **Exact Code Fix:**
  ```python
  from langgraph.graph import StateGraph, START, END
  from langgraph.checkpoint.memory import MemorySaver
  from app.schemas.working_memory import WorkingMemoryState
  from app.core.config import settings

  def process_memory(state: WorkingMemoryState):
      return {}

  graph_builder = StateGraph(WorkingMemoryState)
  graph_builder.add_node("process", process_memory)
  graph_builder.add_edge(START, "process")
  graph_builder.add_edge("process", END)

  # In-memory checkpointer safe for unit tests and local dev
  checkpointer = MemorySaver()
  working_memory_engine = graph_builder.compile(checkpointer=checkpointer)
  ```

#### 3.3 Add Missing Imports in Lifecycle Service
* **File:** `app/services/research/lifecycle.py`
* **Lines:** 1–6, 41, 82
* **Bug / Error:** `start_time: Optional[datetime]` lacks `from datetime import datetime`. Line 82 calls `ResearchMetricsService` without import. Calling `transition_run(..., start_time=...)` raises `NameError`.
* **Exact Code Fix:**
  Add imports at top of `lifecycle.py`:
  ```python
  from datetime import datetime
  from app.services.research.metrics import ResearchMetricsService
  ```

#### 3.4 Align Report Citation Mapping
* **File:** `app/services/research/provenance.py`
* **Function:** `audit_claim_citations()` (lines 76–93)
* **Bug / Error:** Assumes `report.citations` is a dict of `{claim_id: [evidence_ids]}`. When citations are list format or embedded in markdown, it crashes with `AttributeError`.
* **Exact Code Fix:**
  Support flexible extraction:
  ```python
  citations = report.citations or {}
  if isinstance(citations, dict):
      evidence_id_list = []
      for val in citations.values():
          if isinstance(val, list):
              evidence_id_list.extend(val)
          elif isinstance(val, (str, uuid.UUID)):
              evidence_id_list.append(val)
  elif isinstance(citations, list):
      evidence_id_list = citations
  else:
      evidence_id_list = []

  for ev_id in evidence_id_list:
      ev_uuid = uuid.UUID(str(ev_id))
      ev_result = await self.session.execute(
          select(ResearchEvidence).where(
              ResearchEvidence.evidence_id == ev_uuid,
              ResearchEvidence.run_id == run_id
          )
      )
      if not ev_result.scalars().first():
          raise ValueError(f"Fabricated citation {ev_uuid}")
  ```

---

# PHASE 2: Governance, Scalability & Production Verification

---

### Ticket 4: Admission Control, Redis Rate Limiting & Worker Pool Isolation

#### 4.1 Deduplicate and Align `ResearchAdmissionController`
* **File:** `app/services/research/admission.py`
* **Lines:** 27–127
* **Bug / Error:** Lines 74–116 duplicate lines 27–73. Calls non-existent methods `check_user_concurrency()`, `check_workspace_concurrency()`, `check_global_concurrency()`, `check_rate_limit()`, and `get_user_concurrency_status()`.
* **Exact Code Fix:**
  Replace `admit_research_run()` and `get_queue_status()` with clean, deduplicated implementation:
  ```python
  async def admit_research_run(
      self,
      workspace_id: UUID,
      owner_id: UUID,
      objective: str,
      engine: str,
      engine_revision: Optional[str] = None
  ) -> ResearchRun:
      # 1. Enforce user concurrency quota
      if await self.quota_service.enforce_user_quota(owner_id) == "QUOTA_EXCEEDED":
          raise HTTPException(
              status_code=status.HTTP_429_TOO_MANY_REQUESTS,
              detail="User research concurrency quota exceeded"
          )

      # 2. Enforce workspace concurrency quota
      if await self.quota_service.enforce_workspace_quota(workspace_id) == "QUOTA_EXCEEDED":
          raise HTTPException(
              status_code=status.HTTP_429_TOO_MANY_REQUESTS,
              detail="Workspace research concurrency quota exceeded"
          )

      # 3. Enforce global concurrency quota
      if await self.quota_service.enforce_global_quota() == "QUOTA_EXCEEDED":
          raise HTTPException(
              status_code=status.HTTP_429_TOO_MANY_REQUESTS,
              detail="Global research concurrency quota exceeded"
          )

      # 4. Enforce provider rate limits
      if engine == "open_deep_research":
          if not await self.rate_limiter.enforce_rate_limit("llm", owner_id):
              raise HTTPException(
                  status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                  detail="LLM provider rate limit exceeded"
              )
          if not await self.rate_limiter.enforce_rate_limit("search", workspace_id):
              raise HTTPException(
                  status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                  detail="Search provider rate limit exceeded"
              )

      # 5. Create canonical ResearchRun
      return await self.repository.create_run(
          workspace_id=workspace_id,
          owner_id=owner_id,
          objective=objective,
          engine=engine,
          engine_revision=engine_revision
      )

  async def get_queue_status(self) -> Dict[str, Any]:
      return {
          "user_limits": {"limit": self.quota_service.user_concurrency_limit},
          "workspace_limits": {"limit": self.quota_service.workspace_concurrency_limit},
          "global_limits": {"limit": self.quota_service.global_concurrency_limit},
          "rate_limits": await self.rate_limiter.get_rate_limit_status()
      }
  ```

#### 4.2 Prevent Redis Memory Leaks & Key Collisions in Rate Limiter
* **File:** `app/services/research/rate_limiter.py`
* **Function:** `enforce_rate_limit()` (lines 43–48)
* **Bug / Error:** Line 47 calls `zadd(key, {now.timestamp(): now.timestamp()})`. No TTL (`expire`) is set, so keys leak in Redis indefinitely under 1,000 users. Identical float member/score collides on sub-millisecond concurrent requests.
* **Exact Code Fix:**
  ```python
  import uuid

  # In enforce_rate_limit():
  if len(timestamps) >= current_limit:
      return False

  # Use unique member string to prevent timestamp collision
  member = f"{now.timestamp()}:{uuid.uuid4()}"
  await self.redis_client.zadd(key, {member: now.timestamp()})
  # Set TTL to 2x the window so expired keys are automatically reclaimed by Redis
  await self.redis_client.expire(key, window_seconds * 2)
  return True
  ```

#### 4.3 Add `"finalizing"` to Active Quota Statuses
* **File:** `app/services/research/quota.py`
* **Lines:** 77, 91, 105
* **Bug / Error:** `status.in_(["pending", "planning", "researching", "synthesizing"])` omits `"finalizing"`, allowing concurrent runs to exceed quota during report finalization.
* **Exact Code Fix:**
  Update status list to:
  ```python
  ResearchRun.status.in_(["pending", "planning", "researching", "synthesizing", "finalizing"])
  ```

#### 4.4 ARQ Worker Pool Queue Routing & Isolation
* **Files:**
  * `app/workers/settings.py` (lines 84–103)
  * `app/api/routes/workspaces.py` (line 489)
* **Bug / Error:** `WorkerSettings` sets `functions = []` on the class and populates it in `__init__()`, so the ARQ CLI sees an empty list. All jobs are enqueued to default `arq:queue` without queue isolation.
* **Exact Code Fix:**
  * In `app/workers/settings.py`, populate `functions` explicitly on the class:
    ```python
    class WorkerSettings(BaseWorkerSettings):
        functions = [
            run_research_agent_job,
            parse_and_chunk_job,
            compress_episodic_job,
            sync_knowledge_to_graph_job,
            project_output_graph_job,
            export_workspace_job,
            project_to_open_notebook_job,
            process_deletion_tombstone_job,
            reconcile_deletion_tombstones_job
        ]
        queue_name = "research-standard"
        max_jobs = 20
        ...
    ```
  * In `app/api/routes/workspaces.py:489`:
    ```python
    await arq_redis.enqueue_job(
        "run_research_agent_job",
        workspace_id=str(workspace_id),
        objective=request.objective,
        run_id=str(run.run_id),
        _job_id=job_id,
        _queue_name="research-standard"
    )
    ```

#### 4.5 Wire Admission Controller into `workspaces.py` & Register New Routes in `main.py`
* **Files:**
  * `app/api/routes/workspaces.py` (lines 463–498)
  * `app/api/routes/quota.py`
  * `app/api/routes/rate_limiter.py`
  * `app/api/routes/worker.py`
  * `app/api/routes/metrics.py`
  * `app/main.py`
* **Bug / Error:** New routes are not registered in `app/main.py`. Routes import non-existent dependencies from `app.api.deps` and access `.id` on a `UUID`.
* **Exact Code Fix:**
  * In `quota.py`, `rate_limiter.py`, `worker.py`, `metrics.py`:
    ```python
    from app.api.deps.auth import get_current_user
    from app.api.deps.arq import get_arq_redis
    from app.core.database import get_db_session
    # current_user: UUID = Depends(get_current_user)
    ```
  * In `app/api/routes/workspaces.py:463`, inject admission controller:
    ```python
    admission_controller = ResearchAdmissionController(
        quota_service=ResearchQuotaService(research_repo),
        rate_limiter=ProviderRateLimiter(arq_redis),
        repository=research_repo
    )
    run = await admission_controller.admit_research_run(
        workspace_id=workspace_id,
        owner_id=current_user_id,
        objective=request.objective,
        engine=engine
    )
    ```
  * In `app/main.py`, register all routers:
    ```python
    from app.api.routes.quota import router as quota_router
    from app.api.routes.rate_limiter import router as rate_limiter_router
    from app.api.routes.worker import router as worker_router
    from app.api.routes.metrics import router as metrics_router

    app.include_router(quota_router, prefix="/api/v1")
    app.include_router(rate_limiter_router, prefix="/api/v1")
    app.include_router(worker_router, prefix="/api/v1")
    app.include_router(metrics_router, prefix="/api/v1")
    ```

#### 4.6 Open Notebook Capacity Hardening
* **File:** `app/integrations/open_notebook/client.py`
* **Bug / Error:** Unbounded connection instantiation on external Open Notebook service calls.
* **Exact Code Fix:**
  In `OpenNotebookClient`, use a shared connection pool with explicit limits (`max_connections=50`, `max_keepalive_connections=20`, `timeout=30.0`).

---

### Ticket 5: Test Suite Stabilization, Benchmarks & Final Verification

#### 5.1 Fix Python Syntax Error in Rollback Test
* **File:** `tests/integration/benchmark/test_rollback_verification.py`
* **Line:** 48
* **Bug / Error:** Contains `// we rely on the fact that...`. C++ comment syntax causes immediate `SyntaxError: invalid syntax` on pytest collection.
* **Exact Code Fix:**
  Change `//` to `#`:
  ```python
  # we rely on the fact that the run completed successfully under the legacy engine setting.
  ```

#### 5.2 Fix Terminal State Transition Crash in Failure Test
* **File:** `tests/integration/benchmark/test_failure_injection.py`
* **Function:** `test_redis_saturation_handling()` (lines 65–71)
* **Bug / Error:** Loop transitions the same run to `"completed"` on iteration 0, then tries to transition to `"planning"` on iteration 1. Raises `InvalidTransitionError`.
* **Exact Code Fix:**
  Create a new `run` inside the loop for each iteration:
  ```python
  for i in range(10):
      iter_run = await repo.create_run(workspace.workspace_id, uuid.uuid4(), f"Saturation test {i}", "legacy")
      await lifecycle.transition_run(workspace.workspace_id, iter_run.run_id, "planning")
      await lifecycle.transition_run(workspace.workspace_id, iter_run.run_id, "researching")
      await lifecycle.transition_run(workspace.workspace_id, iter_run.run_id, "completed")
  ```

#### 5.3 Remove Global Module Mocking Pollution in Tests
* **Files:**
  * `tests/integration/test_phase4_evaluation.py` (lines 10–11)
  * `tests/unit/test_ground_engine_factory.py` (lines 8–9)
* **Bug / Error:** Top-level assignment `sys.modules['langgraph'] = MagicMock()` globally pollutes `sys.modules` for all subsequently collected tests, breaking `tests/test_working_memory.py`.
* **Exact Code Fix:**
  Remove top-level `sys.modules['langgraph'] = MagicMock()` from both files. Use `unittest.mock.patch` inside specific test functions that require mocking.

#### 5.4 Fix Benchmark Runner Script Issues
* **Files:**
  * `scripts/benchmark_runner.py` (lines 93–94, 118, 175)
  * `scripts/load_benchmark.py` (lines 58–66, 80)
* **Bug / Error:**
  * `benchmark_runner.py`: Passes string UUIDs to `astream_events()`; sets `llm_gateway = None` for real-provider tier, crashing on `TypeError: 'NoneType' object is not callable`.
  * `load_benchmark.py`: Session is closed immediately in `setup()`; passes integer string `UUID("1")`, crashing with `ValueError`.
* **Exact Code Fix:**
  * In `benchmark_runner.py`: Pass `UUID(run_id)` and `UUID(workspace_id)`. Supply a working LLM callable for real-provider tier. Read cost from `ResearchUsage`.
  * In `load_benchmark.py`: Generate valid `uuid.uuid4()` for `owner_id`. Scope session per user simulation.

#### 5.5 Restore Acceptance Gates in `GATES.md` & Validate
* **Files:**
  * `GATES.md`
  * `scripts/check_gates.py`
* **Bug / Error:** `GATES.md` had 57 gates deleted to fake a 100% pass rate. `check_gates.py` only grepped for `[x]` strings.
* **Exact Code Fix:**
  * Restore the full 60 acceptance criteria gates from Section 56 of `NEOSISLM_CHAPTER_2_3_REMEDIATION_DESIGN.md`.
  * Update `scripts/check_gates.py` to run automated verification:
    ```bash
    pytest tests/
    ```
  * Verify that all 60 gates legitimately pass with 0 errors and 0 failures.
