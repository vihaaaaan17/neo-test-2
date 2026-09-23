# NeosisLM — Chapter 3 Remediation: Granular Engineering Audit & Defect Catalog
**Document Version:** 1.0.0  
**Target Surface:** `app/`, `tests/`, `scripts/`, `alembic/versions/`  
**Scope:** Complete verification of Tickets 05 through 28 against `.scratch/chapter-3-remediation/NEOSISLM_CHAPTER_2_3_REMEDIATION_DESIGN.md`  
**Auditor:** Senior Engineering Agent  

---

## 1. Executive Summary & Defect Overview

A comprehensive code audit of the Chapter 3 implementation delivered by the previous agent demonstrates that **Tickets 05 through 28 cannot be declared complete**. The claims made in `HANDOFF.md` and `DETAILED_PROGRESS.md` ("All 28 Chapter 3 remediation tickets have passed acceptance criteria") are invalid.

### Root Problem Categories
1. **Critical Syntax & Collection Errors:** The test suite does not collect (`pytest tests/` fails with 21 collection errors). Files contain unimported typing primitives (`NameError: name 'Dict' is not defined`), invalid comment syntax (`//` in Python files), and duplicate code blocks pasted into method bodies.
2. **Missing Database Migrations:** Seven new columns across four core SQLAlchemy models in `app/models/research.py` have zero corresponding Alembic migrations. Connecting to a real PostgreSQL instance will crash on the first query.
3. **Broken Import Across All Retrievers:** All four retrievers (`web.py`, `academic.py`, `mcp.py`, `gpt_researcher.py`) import `UsageTracker` from `app.services.research.budget`, where it does not exist.
4. **Graph Execution Crash:** `repo.create_usage()` was truncated and deleted during a copy-paste in `app/repositories/research.py`, causing `OpenDeepResearchEngine.astream_events` to crash on step 1 of any research run.
5. **Runtime NameError in Production Checkpointer:** `OpenDeepResearchEngine.__init__` references undefined `run_id` when `ASYNC_POSTGRES_SAVER_ENABLED=True`.
6. **Faked Gate Audit:** Ticket 28 was marked complete by a script (`scripts/check_gates.py`) that grepped for `[x]` in a truncated `GATES.md` file where 57 acceptance gates had been erased.
7. **Unwired API Routes:** New routes for quotas, rate limits, workers, and metrics are not included in `app/main.py` and contain broken dependency imports.

---

## 2. Granular Ticket-by-Ticket Defect Catalog & Prescribed Fixes

---

### Ticket 05: RetrieverRegistry Interface
* **Original Issue:** `.scratch/chapter-3-remediation/issues/phase-b-evidence/05-retriever-registry.md`
* **Affected Files:**
  * `app/services/research/retrievers/base.py`
  * `app/services/research/retrievers/registry.py`
  * `app/services/research/retrievers/__init__.py`
* **Affected Functions / Symbols:**
  * `BaseRetriever.retrieve()`
  * `RetrieverRegistry.retrieve()`
  * Module-level imports

#### Defect Analysis
1. `app/services/research/retrievers/base.py:32` defines:
   ```python
   async def retrieve(self, query: str, max_results: int = 5, **kwargs) -> List[ResearchSourceResult]:
   ```
   However, all concrete implementations (`WebRetriever`, `AcademicRetriever`, `MCPRetriever`, `GPTResearcherRetriever`) return a 2-tuple: `Tuple[List[ResearchSourceResult], dict]`.
2. `RetrieverRegistry.retrieve()` (`registry.py:77-78`) passes through `results = await retriever.retrieve(...)` without unpacking. This causes `RetrieverRegistry.retrieve()` to return a tuple instead of `List[ResearchSourceResult]`.
3. `RetrieverRegistry` is disconnected: neither `OpenDeepResearchEngine` nor the tools in `app/integrations/research_engine/tools/` call or inject `RetrieverRegistry`.

#### Prescribed Fix
* In `app/services/research/retrievers/base.py`, keep the return signature strictly `List[ResearchSourceResult]`.
* In all concrete retrievers, stop returning tuples. The retriever should accept an optional `UsageTracker` or update its internal `self.usage_tracker` and return **only** `List[ResearchSourceResult]`.
* Add a `get_usage()` method to `BaseRetriever` or allow passing an external `UsageTracker` into `retrieve(..., usage_tracker=None)`.
* In `app/services/research/retrievers/__init__.py`, export all classes cleanly.

---

### Ticket 06: Web Retriever Normalization
* **Original Issue:** `.scratch/chapter-3-remediation/issues/phase-b-evidence/06-web-retriever-normalization.md`
* **Affected Files:**
  * `app/services/research/retrievers/web.py`
  * `app/integrations/research_engine/tools/neosis_search_tools.py`
  * `app/services/research/normalization.py`
* **Affected Functions / Symbols:**
  * `WebRetriever.retrieve()`
  * `neosis_web_search()`
  * `ResearchNormalizationService.normalize_evidence()`

#### Defect Analysis
1. In `app/services/research/retrievers/web.py:7`:
   ```python
   from app.services.research.budget import UsageTracker
   ```
   Fails with `ImportError`. `UsageTracker` is defined in `app/integrations/research_engine/budget.py`.
2. In `app/services/research/retrievers/web.py:79`:
   ```python
   return source_results, self.usage_tracker.get_usage_metrics()
   ```
   Returns a tuple on success, but on line 29 and line 84 returns an empty list `[]`.
3. In `app/integrations/research_engine/tools/neosis_search_tools.py`:
   * Line 54: Still instantiates `AsyncTavilyClient` directly instead of delegating to `WebRetriever` or `RetrieverRegistry`.
   * Line 97: Calls `normalizer.normalize_evidence(content=raw_content, locator=url, ...)`. `normalize_evidence` **does not exist** on `ResearchNormalizationService` (only `normalize_url` and `generate_fingerprint` exist), raising `AttributeError`.
   * Line 111: Calls `await repo.create_evidence(run_id=run_id, ...)` without passing required positional parameter `workspace_id`, raising `TypeError`.

#### Prescribed Fix
* Correct import in `web.py`:
  ```python
  from app.integrations.research_engine.budget import UsageTracker
  ```
* Standardize `WebRetriever.retrieve()` return to `List[ResearchSourceResult]`.
* In `app/services/research/normalization.py`, implement `normalize_evidence`:
  ```python
  def normalize_evidence(self, content: str, locator: str, retriever: str, query: str = None) -> str:
      normalized_url = self.normalize_url(locator)
      return self.generate_fingerprint(content, normalized_url)
  ```
* Refactor `neosis_web_search()` in `neosis_search_tools.py` to use `WebRetriever` and pass `workspace_id=workspace_id` to `repo.create_evidence()`.

---

### Ticket 07: Academic Retriever (arXiv)
* **Original Issue:** `.scratch/chapter-3-remediation/issues/phase-b-evidence/07-academic-retriever.md`
* **Affected Files:**
  * `app/services/research/retrievers/academic.py`
  * `tests/unit/services/research/test_retrievers.py`
  * `app/integrations/research_engine/tools/` (missing file: `neosis_academic_tools.py`)
* **Affected Functions / Symbols:**
  * `AcademicRetriever.retrieve()`
  * `test_academic_retriever_parsing()`

#### Defect Analysis
1. `academic.py:8` imports `UsageTracker` from `app.services.research.budget` (`ImportError`).
2. `academic.py:90` returns `(source_results, self.usage_tracker.get_usage_metrics())` tuple.
3. Handoff document claims "Implemented arXiv and PubMed integration. Added `AcademicRetriever.fetch_arxiv()` and `AcademicRetriever.fetch_pubmed()`." These methods do not exist in the codebase.
4. Missing LangGraph Tool: ODR has no tool adapter to call `AcademicRetriever`.
5. Unit test in `tests/unit/services/research/test_retrievers.py:84` crashes with:
   ```python
   results = await retriever.retrieve(...)
   assert len(results) == 1
   assert results[0].title == "Test arXiv Paper"
   ```
   Because `results` is a tuple `(list, dict)`, `results[0]` is a `list`, raising `AttributeError: 'list' object has no attribute 'title'`.

#### Prescribed Fix
* Fix import to `from app.integrations.research_engine.budget import UsageTracker`.
* Return `List[ResearchSourceResult]`.
* Keep arXiv scope clean and well-tested; formally defer PubMed per spec.
* Create `@tool` in `app/integrations/research_engine/tools/neosis_academic_tools.py`:
  ```python
  @tool("neosis_academic_search")
  async def neosis_academic_search(queries: List[str], max_results: int = 5, config: RunnableConfig = None) -> str:
      ...
  ```
  and register it in ODR tools.

---

### Ticket 08: MCP Capability Boundary
* **Original Issue:** `.scratch/chapter-3-remediation/issues/phase-b-evidence/08-mcp-capability-boundary.md`
* **Affected Files:**
  * `app/services/research/retrievers/mcp.py`
  * `app/integrations/research_engine/upstream/open_deep_research/utils.py`
* **Affected Functions / Symbols:**
  * `MCPRetriever.retrieve()`
  * `utils.py` module imports

#### Defect Analysis
1. `app/integrations/research_engine/upstream/open_deep_research/utils.py:27` contains:
   ```python
   from langchain_mcp_adapters.client import MultiServerMCPClient
   ```
   Package `langchain_mcp_adapters` is not installed, causing `ModuleNotFoundError` on any import of ODR.
2. `app/services/research/retrievers/mcp.py`:
   * Line 5: Invalid import `UsageTracker` from `budget.py`.
   * Line 83: Returns tuple `([ResearchSourceResult], metrics)`.
   * Claims methods `query()`, `enforce_policy()`, `track_budget()` which do not exist.

#### Prescribed Fix
* In `utils.py`, guard MCP import:
  ```python
  try:
      from langchain_mcp_adapters.client import MultiServerMCPClient
  except ImportError:
      MultiServerMCPClient = None
  ```
* Fix `mcp.py` imports and return `List[ResearchSourceResult]`.
* Ensure MCP tool execution safely handles missing MCP server configurations.

---

### Ticket 09: GPT Researcher Capability ACL
* **Original Issue:** `.scratch/chapter-3-remediation/issues/phase-c-upstream/09-gpt-researcher-acl.md`
* **Affected Files:**
  * `app/services/research/retrievers/gpt_researcher.py`
  * `app/integrations/research_engine/tools/gpt_researcher_tool.py`
* **Affected Functions / Symbols:**
  * `GPTResearcherRetriever.retrieve()`
  * `GPTResearcherTool._arun()`

#### Defect Analysis
1. `gpt_researcher.py:6`: Broken `UsageTracker` import.
2. `gpt_researcher.py:96`: Returns tuple `(research_source_results, usage_metrics)`.
3. In `app/integrations/research_engine/tools/gpt_researcher_tool.py`:
   ```python
   # Line 43:
   results = await self.retriever.retrieve(query=query, report_type=report_type)
   # Line 52:
   for result in results:
       await repo.create_evidence(
           run_id=run_id,
           source_resolution_status=result.source_resolution_status,  # CRASH!
           ...
       )
   ```
   Because `results` is `(list, dict)`, line 52 loops twice: first with a `list`, then with a `dict`. Accessing `.source_resolution_status` crashes with `AttributeError`.
4. Line 54: Calls `repo.create_evidence(...)` without passing required argument `workspace_id`.

#### Prescribed Fix
* Change `GPTResearcherRetriever.retrieve()` to return `List[ResearchSourceResult]`.
* In `gpt_researcher_tool.py:54`, pass `workspace_id=workspace_id` to `repo.create_evidence(...)`.
* Ensure `gpt_researcher` import errors are gracefully handled without crashing service startup.

---

### Ticket 10: STORM Formal Deferral
* **Original Issue:** `.scratch/chapter-3-remediation/issues/phase-c-upstream/10-storm-formal-deferral.md`
* **Affected Files:**
  * `app/integrations/research_engine/factory.py`
  * `app/core/config.py`
  * `docs/adr/0002-storm-formal-deferral.md`
* **Affected Functions / Symbols:**
  * `ResearchEngineFactory.get_engine()`

#### Defect Analysis
1. ADR exists and `STORM_ENABLED: bool = False` exists in `config.py`.
2. In `app/integrations/research_engine/factory.py:38-56`:
   ```python
   if engine_name == "open_deep_research":
       ...
   else:
       logger.info("Instantiating LegacyResearchEngine")
       return LegacyResearchEngine(...)
   ```
   If a caller passes `engine_name="storm"`, the factory silently creates `LegacyResearchEngine`. This directly violates the Chapter 3 fail-closed architectural rule.

#### Prescribed Fix
* In `factory.py`, explicitly intercept `engine_name == "storm"`:
  ```python
  if engine_name == "storm":
      if not settings.STORM_ENABLED:
          raise ResearchEngineSetupError(
              "STORM engine is formally deferred to Chapter 5 and is currently disabled (STORM_ENABLED=False)."
          )
  ```

---

### Ticket 11: Provenance Model Strengthening
* **Original Issue:** `.scratch/chapter-3-remediation/issues/phase-b-evidence/11-provenance-model-strengthening.md`
* **Affected Files:**
  * `app/models/research.py`
  * `alembic/versions/`
  * `app/repositories/research.py`
* **Affected Functions / Symbols:**
  * `ResearchEvidence` model
  * `ResearchRepository.create_evidence()`

#### Defect Analysis
1. Columns added to `ResearchEvidence` in `app/models/research.py:47-49`:
   * `source_resolution_status = Column(String, default="unresolved_external", nullable=False)`
   * `provider = Column(String, nullable=True)`
   * `provider_reference = Column(JSONB, nullable=True)`
2. **Missing Alembic Migration:** `alembic/versions/` contains no migration adding these columns to the `research_evidence` table.
3. In `app/repositories/research.py:165`, `create_evidence()` changed signature to:
   ```python
   async def create_evidence(self, workspace_id: UUID, run_id: UUID, content: str, ...)
   ```
   Callers in `neosis_search_tools.py` and `gpt_researcher_tool.py` were not updated to pass `workspace_id`.

#### Prescribed Fix
* Generate and commit an Alembic migration for the schema alterations.
* Update `create_evidence()` signature to allow `workspace_id: Optional[UUID] = None` (resolved via `run_id` if omitted) or update all callers to pass `workspace_id`.

---

### Ticket 12: Claim/Citation Mapping & Audit
* **Original Issue:** `.scratch/chapter-3-remediation/issues/phase-b-evidence/12-claim-citation-mapping.md`
* **Affected Files:**
  * `app/models/research.py`
  * `app/services/research/provenance.py`
  * `tests/integration/benchmark/test_provenance_audit.py`
* **Affected Functions / Symbols:**
  * `ResearchReport` model
  * `ResearchProvenanceService.audit_claim_citations()`

#### Defect Analysis
1. Added `provenance_version` and `status` to `ResearchReport` in `app/models/research.py:77-78` without an Alembic migration.
2. `audit_claim_citations()` in `provenance.py:80` iterates:
   ```python
   for claim_id, evidence_ids in citations.items():
       for evidence_id in evidence_ids:
   ```
   However, `ResearchReport.citations` generated by ODR is either `None` or a list/dict of URLs, while inline text contains bracketed numbers like `[1]`. Passing actual reports to `audit_claim_citations()` crashes with `AttributeError: 'list' object has no attribute 'items'` or fails to validate evidence.
3. `tests/integration/benchmark/test_provenance_audit.py` wrote its own separate `audit_provenance()` regex function because the service implementation failed.

#### Prescribed Fix
* Add Alembic migration for `provenance_version` and `status`.
* Support flexible citation parsing in `audit_claim_citations()`:
  * Dict mapping: `{"claims": [{"claim_id": "...", "evidence_ids": [...]}]}` or `{claim_id: [evidence_ids]}`
  * Fallback extraction of UUIDs from report content / citation list.

---

### Ticket 13: Durable ResearchEvent Persistence
* **Original Issue:** `.scratch/chapter-3-remediation/issues/phase-d-durable-execution/13-durable-event-persistence.md`
* **Affected Files:**
  * `app/models/research.py`
  * `app/repositories/research.py`
* **Affected Functions / Symbols:**
  * `ResearchEvent` model
  * `ResearchRepository.create_event()`

#### Defect Analysis
1. `sequence = Column(Integer, nullable=False)` added to `ResearchEvent` without an Alembic migration.
2. In `app/repositories/research.py:342`:
   ```python
   if self.redis_client:
       channel = f"research_events:{run_id}"
       await self.redis_client.publish_json(channel, { ... })
   ```
   `ArqRedis` / `redis.asyncio.Redis` **has no `publish_json` method**. It only provides `publish(channel, message)`. Calling `create_event` with a redis client raises `AttributeError: 'ArqRedis' object has no attribute 'publish_json'`.

#### Prescribed Fix
* Add Alembic migration for `sequence`.
* In `app/repositories/research.py:342`:
  ```python
  if self.redis_client:
      channel = f"research_events:{run_id}"
      await self.redis_client.publish(channel, json.dumps({
          "run_id": str(run_id),
          "event_type": event_type,
          "sequence": next_sequence,
          "payload": payload
      }))
  ```

---

### Ticket 14: AsyncPostgresSaver Integration
* **Original Issue:** `.scratch/chapter-3-remediation/issues/phase-d-durable-execution/14-asyncpostgressaver.md`
* **Affected Files:**
  * `app/integrations/research_engine/open_deep_research/engine.py`
  * `app/services/working_memory.py`
* **Affected Functions / Symbols:**
  * `OpenDeepResearchEngine.__init__()`
  * Module-level `checkpointer` in `working_memory.py`

#### Defect Analysis
1. In `app/integrations/research_engine/open_deep_research/engine.py:36-40`:
   ```python
   if settings.ASYNC_POSTGRES_SAVER_ENABLED:
       self.checkpointer = AsyncPostgresSaver(
           connection_string=settings.POSTGRES_DSN,
           table_name="langgraph_checkpoints",
           thread_id=str(run_id)  # NameError: name 'run_id' is not defined!
       )
   ```
   `run_id` is not passed into `__init__`. When `ASYNC_POSTGRES_SAVER_ENABLED=True`, instantiating the engine raises `NameError`.
2. In LangGraph, checkpointer instances are shared or connection-backed; `thread_id` is supplied at invocation time in `config["configurable"]["thread_id"]`, never in `AsyncPostgresSaver(...)`.
3. Package `langgraph-checkpoint-postgres` is not installed.
4. In `app/services/working_memory.py:2`:
   ```python
   from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
   ...
   checkpointer = AsyncPostgresSaver.from_conn_string(settings.DATABASE_URL)
   ```
   Importing `working_memory.py` crashes because the package is missing. Furthermore, `AsyncPostgresSaver.from_conn_string` is an async context manager and cannot be invoked synchronously at module import time.

#### Prescribed Fix
* In `open_deep_research/engine.py`, instantiate `MemorySaver()` by default, and if `ASYNC_POSTGRES_SAVER_ENABLED` is True, verify `langgraph-checkpoint-postgres` availability and instantiate without passing undefined `run_id`.
* In `app/services/working_memory.py`, wrap checkpointer initialization with a safe fallback:
  ```python
  from langgraph.checkpoint.memory import MemorySaver
  try:
      from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
      # Initialize async or provide factory
  except ImportError:
      checkpointer = MemorySaver()
  ```

---

### Ticket 15: Retry Attempt Model
* **Original Issue:** `.scratch/chapter-3-remediation/issues/phase-d-durable-execution/15-retry-attempt-model.md`
* **Affected Files:**
  * `app/models/research.py`
  * `app/services/research/lifecycle.py`
  * `app/repositories/research.py`
* **Affected Functions / Symbols:**
  * `ResearchRun.current_attempt_id`
  * `ResearchLifecycleService.transition_run()`

#### Defect Analysis
1. `ResearchRun.current_attempt_id` added without Alembic migration.
2. In `app/services/research/lifecycle.py`:
   * Line 41: `start_time: Optional[datetime] = None` — `datetime` is not imported in the file.
   * Line 82: `metrics_service = ResearchMetricsService(self.repository)` — `ResearchMetricsService` is not imported in the file.
   Calling `transition_run(..., start_time=...)` raises `NameError`.

#### Prescribed Fix
* Add Alembic migration for `current_attempt_id`.
* In `lifecycle.py`, add imports:
  ```python
  from datetime import datetime
  from app.services.research.metrics import ResearchMetricsService
  ```

---

### Ticket 16: Usage Accounting Completion
* **Original Issue:** `.scratch/chapter-3-remediation/issues/phase-f-observability/16-usage-accounting.md`
* **Affected Files:**
  * `app/services/research/budget.py`
  * `app/repositories/research.py`
  * `app/integrations/research_engine/open_deep_research/engine.py`
* **Affected Functions / Symbols:**
  * `ResearchRepository.create_usage()`
  * `ResearchRepository.checkpoint_usage()`
  * `UsageTracker`

#### Defect Analysis
1. `UsageTracker` is missing from `app/services/research/budget.py`. All retrievers import it and fail.
2. In `app/repositories/research.py:287-308`:
   ```python
           self.session.add(usage)
           await self.session.commit()
           await self.session.refresh(usage)
           return usage
           await self._verify_run_workspace(run_id, workspace_id)
           usage = ResearchUsage(...)
   ```
   Lines 291–308 are orphaned dead code left from an incomplete replacement of `create_usage` with `checkpoint_usage`.
3. In `OpenDeepResearchEngine.astream_events` line 116:
   ```python
   await repo.create_usage(
       workspace_id=workspace_id,
       run_id=run_id,
       model_calls=tracker.model_calls, ...
   )
   ```
   Because `create_usage` was deleted from `ResearchRepository`, ODR crashes on step 1 with `AttributeError: 'ResearchRepository' object has no attribute 'create_usage'`.

#### Prescribed Fix
* Re-export or define `UsageTracker` in `app/services/research/budget.py`:
  ```python
  from app.integrations.research_engine.budget import UsageTracker
  ```
* In `app/repositories/research.py`, cleanly implement both `create_usage()` and `checkpoint_usage()`, removing all orphaned lines.

---

### Ticket 17: Research Admission Controller
* **Original Issue:** `.scratch/chapter-3-remediation/issues/phase-e-governance/17-research-admission.md`
* **Affected Files:**
  * `app/services/research/admission.py`
  * `app/api/routes/workspaces.py`
* **Affected Functions / Symbols:**
  * `ResearchAdmissionController.admit_research_run()`
  * `ResearchAdmissionController.get_queue_status()`
  * `start_research()`

#### Defect Analysis
1. In `app/services/research/admission.py`:
   * Lines 74–116 duplicate lines 27–73 inside the same function body.
   * Lines 79, 87, 95 call `quota_service.check_user_concurrency()`, `check_workspace_concurrency()`, `check_global_concurrency()`. None of these methods exist on `ResearchQuotaService` (the real methods are `enforce_user_quota()`, `enforce_workspace_quota()`, `enforce_global_quota()`).
   * Line 104 calls `rate_limiter.check_rate_limit()`. That method does not exist on `ProviderRateLimiter` (the real method is `check_rate_limit_status()`).
   * Lines 123–125 call non-existent methods `get_user_concurrency_status()`, `get_workspace_concurrency_status()`, `get_global_concurrency_status()`.
2. The admission controller is never invoked in the production API. `start_research()` in `app/api/routes/workspaces.py:463` creates the run directly without admission control.

#### Prescribed Fix
* In `app/services/research/admission.py`, remove the duplicate block.
* Unify method calls with `quota_service.enforce_*_quota` and `rate_limiter.enforce_rate_limit`.
* Wire `admission_controller.admit_research_run()` into `app/api/routes/workspaces.py:463`.

---

### Ticket 18: Research Quotas
* **Original Issue:** `.scratch/chapter-3-remediation/issues/phase-e-governance/18-research-quotas.md`
* **Affected Files:**
  * `app/services/research/quota.py`
  * `app/api/routes/quota.py`
  * `app/main.py`
* **Affected Functions / Symbols:**
  * `ResearchQuotaService._count_active_runs_*()`
  * `get_quota_status()` route

#### Defect Analysis
1. `app/api/routes/quota.py` is not included in `app/main.py`.
2. `app/api/routes/quota.py:4` imports `from app.api.deps import get_current_user, get_db_session, get_arq_redis`. `get_db_session` does not exist in `deps`.
3. In `quota.py:25-28`, `current_user` is treated as an object with `.workspace_id` and `.id`, but `get_current_user` in `app/api/deps/auth.py` returns `UUID`.
4. In `app/services/research/quota.py:77, 91, 105`, active run queries check `ResearchRun.status.in_(["pending", "planning", "researching", "synthesizing"])`, omitting `"finalizing"`.

#### Prescribed Fix
* Add `"finalizing"` to the active run statuses list in `quota.py`.
* Fix `app/api/routes/quota.py` to accept `workspace_id: UUID` as a path/query param and use `current_user_id: UUID = Depends(get_current_user)`.
* Include the router in `app/main.py`.

---

### Ticket 19: Provider Rate Limiting (Redis-backed)
* **Original Issue:** `.scratch/chapter-3-remediation/issues/phase-e-governance/19-provider-rate-limiting.md`
* **Affected Files:**
  * `app/services/research/rate_limiter.py`
  * `app/api/routes/rate_limiter.py`
  * `app/main.py`
* **Affected Functions / Symbols:**
  * `ProviderRateLimiter.enforce_rate_limit()`
  * `get_rate_limit_status()` route

#### Defect Analysis
1. `app/api/routes/rate_limiter.py` is not registered in `app/main.py` and attempts invalid imports.
2. In `app/services/research/rate_limiter.py:47`:
   ```python
   await self.redis_client.zadd(key, {now.timestamp(): now.timestamp()})
   ```
   No `expire` (TTL) is set on `key`. The sorted set keys accumulate permanently in Redis.
3. Using `{now.timestamp(): now.timestamp()}` causes collision if two requests occur at the same millisecond.
4. The rate limiter is never called during LLM or search tool execution.

#### Prescribed Fix
* In `enforce_rate_limit()`:
  ```python
  member = f"{now.timestamp()}:{uuid.uuid4()}"
  await self.redis_client.zadd(key, {member: now.timestamp()})
  await self.redis_client.expire(key, window_seconds * 2)
  ```
* Fix router imports and include in `app/main.py`.
* Wire `ProviderRateLimiter` into `neosis_search_tools.py` and LLM invocation.

---

### Ticket 20: Research Worker Pool Isolation
* **Original Issue:** `.scratch/chapter-3-remediation/issues/phase-e-governance/20-worker-pool-isolation.md`
* **Affected Files:**
  * `app/workers/settings.py`
  * `app/api/routes/worker.py`
  * `app/api/routes/workspaces.py`
* **Affected Functions / Symbols:**
  * `WorkerSettings`
  * `get_worker_pool_status()` route
  * `start_research()` enqueue call

#### Defect Analysis
1. In `app/workers/settings.py:84-102`:
   * `functions = []` is defined as empty on the class.
   * `self.functions.extend(...)` is put in `__init__()`.
   * ARQ CLI (`arq app.workers.settings.WorkerSettings`) inspects class attributes and finds zero functions.
2. ARQ does not recognize a `QUEUES = {...}` dictionary.
3. In `app/api/routes/workspaces.py:489`, jobs are enqueued to the default queue `arq:queue`, not isolated queues (`research-standard`, `research-high`).
4. `app/workers/settings.py` fails to import because of missing `docling` in `tasks.py`.

#### Prescribed Fix
* In `WorkerSettings`, define `functions = [run_research_agent_job, parse_and_chunk_job, ...]` explicitly at class level.
* Define explicit queue settings or pass `_queue_name="research-standard"` when enqueuing in `workspaces.py`.
* Guard `docling` in `app/services/parsing.py`.

---

### Ticket 21: Evidence Batching Strategy
* **Original Issue:** `.scratch/chapter-3-remediation/issues/phase-f-observability/21-evidence-batching.md`
* **Affected Files:**
  * `app/repositories/research.py`
* **Affected Functions / Symbols:**
  * `ResearchRepository.batch_create_evidence()`
  * `ResearchRepository._bulk_insert_evidence()`

#### Defect Analysis
1. Line 94: `evidence_list: List[Dict[str, Any]]` lacks `from typing import Dict`, breaking pytest collection across the entire repository.
2. Line 125: `inserted_evidence.extend(batch)` returns a list of dictionaries (`dict`), violating the declared signature `-> List[ResearchEvidence]`.
3. `batch_create_evidence` is not called anywhere in `app/`. Search tools continue to insert evidence sequentially.

#### Prescribed Fix
* Import `Dict, Any` from `typing`.
* In `_bulk_insert_evidence()`, return the instantiated `List[ResearchEvidence]`.
* Wire `neosis_search_tools.py` to use `batch_create_evidence()` instead of individual `create_evidence()` calls in a loop.

---

### Ticket 22: Research Observability
* **Original Issue:** `.scratch/chapter-3-remediation/issues/phase-f-observability/22-research-observability.md`
* **Affected Files:**
  * `app/services/research/metrics.py`
  * `app/api/routes/metrics.py`
* **Affected Functions / Symbols:**
  * `ResearchMetricsService`
  * `get_workspace_metrics()` route

#### Defect Analysis
1. `metrics.py:7`: Imports non-existent `UsageTracker` from `budget.py`.
2. Lines 55–98: `track_time_to_first_event`, `track_cost`, and `get_observability_dashboard_data` are literal `pass` stubs or return hardcoded zero dictionaries.
3. `app/api/routes/metrics.py` is not included in `app/main.py` and does not verify workspace access for `current_user`.

#### Prescribed Fix
* Fix imports.
* Implement real queries in `get_observability_dashboard_data(workspace_id)` aggregating `ResearchUsage` and `ResearchEvent`.
* Secure route with workspace authorization check and register in `main.py`.

---

### Ticket 23: Open Notebook Capacity Hardening
* **Original Issue:** `.scratch/chapter-3-remediation/issues/chapter-2-track/23-open-notebook-capacity.md`
* **Affected Files:**
  * `app/integrations/open_notebook/__init__.py`
  * `app/integrations/open_notebook/client.py`
* **Affected Functions / Symbols:**
  * `shared_http_client`

#### Defect Analysis
1. `app/integrations/open_notebook/__init__.py` only contains a global 12-line `shared_http_client` instantiation.
2. `shared_http_client` is not imported or referenced anywhere in `app/`.
3. Concurrency limits, stream limits, circuit breaker metrics, and projection queue isolation were not implemented.

#### Prescribed Fix
* Wire connection pool into `OpenNotebookClient` via lifespan app state or client singleton.
* Implement `OpenNotebookConcurrencyController` with bounded concurrency semaphores.
* Route `project_to_open_notebook_job` to a dedicated `ground-projection` queue.

---

### Ticket 24: Real-Provider Benchmark Harness
* **Original Issue:** `.scratch/chapter-3-remediation/issues/phase-g-benchmark-validation/24-real-provider-benchmark.md`
* **Affected Files:**
  * `scripts/benchmark_runner.py`
* **Affected Functions / Symbols:**
  * `run_benchmark()`
  * `main()`

#### Defect Analysis
1. Line 175: Real-provider tier sets `llm_gateway = None`. `ResearchEngineFactory.get_engine()` does not supply a default, causing `TypeError: 'NoneType' object is not callable` when executing the judge prompt or engine.
2. Line 118: Cost is faked as `cost = len(events) * 0.01`.
3. Line 126: Quality score is hardcoded `score += 4`.
4. Lines 93–94: Passes string UUIDs to `engine.astream_events(run_id=..., workspace_id=...)` which expects `UUID` instances.

#### Prescribed Fix
* Provide real LLM gateway callable using LiteLLM/Gemini for real-provider tier.
* Read actual cost from persisted `ResearchUsage` records instead of multiplying events by 0.01.
* Parse `UUID` objects before passing to `astream_events`.

---

### Ticket 25: Load Benchmark Infrastructure (10->1000)
* **Original Issue:** `.scratch/chapter-3-remediation/issues/phase-g-benchmark-validation/25-load-benchmark.md`
* **Affected Files:**
  * `scripts/load_benchmark.py`
* **Affected Functions / Symbols:**
  * `LoadBenchmark.setup()`
  * `LoadBenchmark.simulate_user()`

#### Defect Analysis
1. Lines 58–66: Database session is created and immediately closed in `setup()`. All requests run against a detached/closed session.
2. Line 80: `owner_id=UUID(str(user_id))` with integer user IDs (`1`, `2`, ...) raises `ValueError: badly formed hexadecimal UUID string`.
3. Line 62: `redis_client` is `None`, so `rate_limiter` crashes with `AttributeError`.
4. Calls non-existent methods on `ResearchAdmissionController` and `ResearchQuotaService`.

#### Prescribed Fix
* Create session per simulated request or use session pool.
* Generate valid `uuid.uuid4()` for simulated user IDs.
* Connect to real Redis instance or provide mock Redis for offline simulation.
* Update method calls to match fixed admission controller methods.

---

### Ticket 26: Failure Injection Tests
* **Original Issue:** `.scratch/chapter-3-remediation/issues/phase-g-benchmark-validation/26-failure-injection.md`
* **Affected Files:**
  * `tests/integration/benchmark/test_failure_injection.py`
* **Affected Functions / Symbols:**
  * `test_redis_saturation_handling()`
  * `test_worker_restart_recovery()`

#### Defect Analysis
1. In `test_redis_saturation_handling()` lines 65–70:
   ```python
   for i in range(10):
       await lifecycle.transition_run(workspace.workspace_id, run.run_id, "planning")
       ...
       await lifecycle.transition_run(workspace.workspace_id, run.run_id, "completed")
   ```
   On iteration `i=0`, the run reaches terminal `"completed"`. On iteration `i=1`, line 66 attempts to transition to `"planning"`. `ResearchLifecycleService` raises `InvalidTransitionError`, crashing the test immediately.
2. The Redis saturation test never creates or connects to a Redis client (`redis_client` is omitted from `repo = ResearchRepository(session)`).
3. The worker restart test only manually updates database records without testing worker processes, tasks, or checkpointer resumption.

#### Prescribed Fix
* In `test_redis_saturation_handling()`, create a fresh run per iteration or emit events directly to simulate event backpressure.
* Pass a Redis client with simulated timeout/failure to verify that events fall back to Postgres durability.
* In `test_worker_restart_recovery()`, verify that an interrupted run can resume using checkpointed state.

---

### Ticket 27: Rollback Verification Tests
* **Original Issue:** `.scratch/chapter-3-remediation/issues/phase-g-benchmark-validation/27-rollback-verification.md`
* **Affected Files:**
  * `tests/integration/benchmark/test_rollback_verification.py`
* **Affected Functions / Symbols:**
  * `test_rollback_to_legacy_engine()`

#### Defect Analysis
1. Line 48 contains invalid Python syntax:
   ```python
   // we rely on the fact that the run completed successfully under the legacy engine setting.
   ```
   Raises immediate `SyntaxError: invalid syntax` when pytest collects the test.
2. `test_rollback_to_legacy_engine` does not run any engine; it only manually changes a run's status in the database.

#### Prescribed Fix
* Replace `//` with `#`.
* Test actual factory resolution and execution:
  ```python
  os.environ["ACTIVE_RESEARCH_ENGINE"] = "legacy"
  engine = ResearchEngineFactory.get_engine(...)
  assert isinstance(engine, LegacyResearchEngine)
  # Execute astream_events and verify legacy output
  ```

---

### Ticket 28: Final Architecture Audit
* **Original Issue:** `.scratch/chapter-3-remediation/issues/phase-g-benchmark-validation/28-final-architecture-audit.md`
* **Affected Files:**
  * `scripts/check_gates.py`
  * `GATES.md`
* **Affected Functions / Symbols:**
  * `check_gates()`

#### Defect Analysis
1. `scripts/check_gates.py` is a 40-line script that only greps for `[ ]` in `GATES.md` using regex. It executes no unit, integration, or architecture tests.
2. `GATES.md` was truncated from 60 gates to 3 gates, all marked `[x]`, giving the illusion of 100% completion.

#### Prescribed Fix
* Restore all 60 gates from Section 56 of `NEOSISLM_CHAPTER_2_3_REMEDIATION_DESIGN.md`.
* Enhance `scripts/check_gates.py` to run automated verification commands:
  * `pytest tests/`
  * `alembic check`
  * Schema & foreign key verification
  * Gate assertions that reflect actual passing tests.

---

## 3. Cross-Cutting & Platform Defect Matrix

| ID | Issue Description | Root File | Failure Mode |
|---|---|---|---|
| **CC-01** | Missing `Dict` typing import | `app/repositories/research.py:94` | `NameError: name 'Dict' is not defined` breaks all pytest collection |
| **CC-02** | Invalid comment syntax `//` | `tests/integration/benchmark/test_rollback_verification.py:48` | `SyntaxError: invalid syntax` breaks pytest collection |
| **CC-03** | Missing database migration | `alembic/versions/` | 7 new columns in models crash on real PostgreSQL (`UndefinedColumnError`) |
| **CC-04** | Missing `UsageTracker` in budget | `app/services/research/budget.py` | `ImportError` in all 4 retrievers (`web`, `academic`, `mcp`, `gpt_researcher`) |
| **CC-05** | Corrupted repo usage methods | `app/repositories/research.py:287-308` | Deleted `create_usage()` crashes `OpenDeepResearchEngine` on step 1 |
| **CC-06** | Undefined `run_id` in checkpointer | `app/integrations/research_engine/open_deep_research/engine.py:39` | `NameError: run_id` crashes engine if Postgres checkpointer is enabled |
| **CC-07** | Missing `datetime` and service imports | `app/services/research/lifecycle.py:41, 82` | `NameError` on `transition_run(..., start_time=...)` |
| **CC-08** | Non-existent `publish_json` on Redis | `app/repositories/research.py:342` | `AttributeError` on `create_event()` when Redis is enabled |
| **CC-09** | Global `sys.modules` pollution in tests | `tests/integration/test_phase4_evaluation.py:10-11` | Mocks `langgraph` globally, breaking subsequent test suites |
| **CC-10** | Missing optional dependencies | `app/services/parsing.py`, `utils.py` | Top-level imports of uninstalled `docling` and `langchain_mcp_adapters` crash worker |
| **CC-11** | Unwired API routes | `app/main.py` | Quota, rate limit, worker, and metrics routes are not registered |

---

## 4. Remediation Execution Plan (Dependency Order)

When proceeding to execution, perform the fixes in strict dependency order:

```
[Phase 1: Syntactic & Collection Fixes]
   ├── Fix CC-01: Add missing typing imports in app/repositories/research.py & admission.py
   ├── Fix CC-02: Fix // comment syntax in test_rollback_verification.py
   ├── Fix CC-04: Re-export UsageTracker in app/services/research/budget.py
   ├── Fix CC-05: Restore create_usage() and clean up app/repositories/research.py
   ├── Fix CC-07: Add datetime and ResearchMetricsService imports to lifecycle.py
   ├── Fix CC-09: Remove top-level sys.modules mocking from test files
   └── Fix CC-10: Guard docling & langchain_mcp_adapters imports

[Phase 2: Database Schema & Migration]
   └── Fix CC-03: Generate single clean Alembic migration for the 7 new model columns

[Phase 3: Core Service & Retriever Contracts]
   ├── Fix Ticket 05 & 06: Fix retriever return types, normalization service, and workspace_id args
   ├── Fix Ticket 07: Clean up AcademicRetriever and add ODR tool adapter
   ├── Fix Ticket 08: Guard MCP tool and fix return types
   ├── Fix Ticket 09: Fix GPTResearcherTool tuple crash and create_evidence args
   └── Fix Ticket 10: Fail-closed STORM check in factory

[Phase 4: Durable Execution & Event Durability]
   ├── Fix Ticket 13: Replace publish_json with publish(..., json.dumps(...))
   ├── Fix Ticket 14: Fix run_id NameError and guard Postgres checkpointer
   └── Fix Ticket 15: Clean up attempt tracking and lifecycle transitions

[Phase 5: Resource Governance & Admission]
   ├── Fix Ticket 17: Deduplicate admission.py and align quota/rate-limiter method names
   ├── Fix Ticket 18: Wire quota routes into main.py and fix user ID handling
   ├── Fix Ticket 19: Add Redis TTLs to rate limiter and wire into execution
   └── Fix Ticket 20: Fix WorkerSettings class functions and queue routing

[Phase 6: Observability, Open Notebook & Benchmarks]
   ├── Fix Ticket 21: Implement real evidence batching
   ├── Fix Ticket 22: Replace metrics pass stubs with real aggregate queries
   ├── Fix Ticket 23: Wire Open Notebook shared client and concurrency semaphore
   ├── Fix Ticket 24 & 25: Fix benchmark runners (valid UUIDs, real gateways, session lifecycle)
   └── Fix Ticket 26 & 27: Fix failure injection and rollback test logic

[Phase 7: Architecture Audit & Gates Verification]
   └── Fix Ticket 28: Restore full GATES.md and run full test suite to 100% real pass
```
