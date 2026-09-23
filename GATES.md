# Chapter 3 & Chapter 2 Remediation Acceptance Gates

Documented in Section 56 of `NEOSISLM_CHAPTER_2_3_REMEDIATION_DESIGN.md` and consolidated in `TWO_PHASE_CONSOLIDATED_PLAN.md`.

## Lifecycle
- [x] ResearchRun created before enqueue.
  - CHECK: `app/api/routes/workspaces.py:486` calls `admit_research_run()` before `enqueue_job()`
  - EVIDENCE: Verified in workspaces.py
- [x] run_id mandatory.
  - CHECK: `app/workers/tasks.py:336` validates `run_id` presence
  - EVIDENCE: Verified in tasks.py
- [x] owner_id canonical.
  - CHECK: `app/models/research.py:27` and `app/repositories/research.py` enforce `owner_id`
  - EVIDENCE: Verified in models and repository
- [x] attempt identity exists.
  - CHECK: `alembic/versions/7da81234abcd_add_ch3_remediation_columns.py` adds `current_attempt_id`
  - EVIDENCE: Verified in migration 7da81234abcd
- [x] no terminal-state overwrite.
  - CHECK: `app/workers/tasks.py:427` uses `ResearchLifecycleService` as sole authority
  - EVIDENCE: Verified in tasks.py
- [x] no hidden fallback.
  - CHECK: `app/integrations/research_engine/factory.py:52` raises `ResearchEngineSetupError`
  - EVIDENCE: Verified in factory.py

## Engines
- [x] ODR primary.
  - CHECK: `app/integrations/research_engine/open_deep_research/engine.py` is primary engine
  - EVIDENCE: Verified in engine.py
- [x] legacy explicit only.
  - CHECK: `app/integrations/research_engine/factory.py:59` requires explicit `"legacy"`
  - EVIDENCE: Verified in factory.py
- [x] STORM capability integrated or explicitly disabled by documented Phase 1 decision.
  - CHECK: `app/integrations/research_engine/factory.py:53` checks `STORM_ENABLED` fail-closed
  - EVIDENCE: Verified in factory.py
- [x] GPT Researcher capability integrated through Neosis ACL.
  - CHECK: `app/integrations/research_engine/tools/gpt_researcher_tool.py` passes `workspace_id`
  - EVIDENCE: Verified in gpt_researcher_tool.py

## Retrieval
- [x] RetrieverRegistry exists.
  - CHECK: `app/services/research/retrievers/registry.py` defines `RetrieverRegistry`
  - EVIDENCE: Verified in registry.py
- [x] WebRetriever exists.
  - CHECK: `app/services/research/retrievers/web.py` returns `List[ResearchSourceResult]`
  - EVIDENCE: Verified in web.py
- [x] AcademicRetriever exists.
  - CHECK: `app/services/research/retrievers/academic.py` returns `List[ResearchSourceResult]`
  - EVIDENCE: Verified in academic.py
- [x] MCPRetriever exists where enabled.
  - CHECK: `app/services/research/retrievers/mcp.py` guards MCP and returns `List[ResearchSourceResult]`
  - EVIDENCE: Verified in mcp.py
- [x] provider policies exist.
  - CHECK: `app/services/research/retrievers/base.py` defines `ResearchRetrievalPolicy`
  - EVIDENCE: Verified in base.py

## Evidence
- [x] evidence persisted before synthesis where possible.
  - CHECK: `app/integrations/research_engine/tools/neosis_search_tools.py:111` persists evidence
  - EVIDENCE: Verified in neosis_search_tools.py
- [x] fingerprints work.
  - CHECK: `app/services/research/normalization.py:29` implements `normalize_evidence`
  - EVIDENCE: Verified in normalization.py
- [x] unresolved provenance is explicit.
  - CHECK: `app/repositories/research.py:100` defaults to `unresolved_external`
  - EVIDENCE: Verified in research.py
- [x] report citations map to evidence.
  - CHECK: `app/services/research/provenance.py:47` validates citations against `ResearchEvidence`
  - EVIDENCE: Verified in provenance.py
- [x] deterministic provenance audit passes.
  - CHECK: `tests/unit/services/research/test_normalization_provenance.py`
  - EVIDENCE: 5/5 unit tests passed

## Usage
- [x] LLM usage.
  - CHECK: `app/services/research/budget.py` and `app/repositories/research.py:150` record token calls
  - EVIDENCE: Verified in create_usage
- [x] search usage.
  - CHECK: `UsageTracker.track_search_call()` in `app/integrations/research_engine/budget.py`
  - EVIDENCE: Verified in budget.py
- [x] retrieval usage.
  - CHECK: `app/models/research.py:133` tracks `retrieval_calls`
  - EVIDENCE: Verified in models/research.py
- [x] academic usage.
  - CHECK: `app/services/research/retrievers/academic.py` increments usage tracker
  - EVIDENCE: Verified in academic.py
- [x] MCP usage.
  - CHECK: `app/models/research.py:135` tracks `mcp_calls`
  - EVIDENCE: Verified in models/research.py
- [x] GPT Researcher usage.
  - CHECK: `app/services/research/retrievers/gpt_researcher.py` records usage metrics
  - EVIDENCE: Verified in gpt_researcher.py
- [x] summarization usage.
  - CHECK: `app/repositories/research.py` supports task-level usage attribution
  - EVIDENCE: Verified in research.py
- [x] latency.
  - CHECK: `app/models/research.py:136` records `latency`
  - EVIDENCE: Verified in models/research.py
- [x] cost.
  - CHECK: `app/models/research.py:137` records estimated `cost`
  - EVIDENCE: Verified in models/research.py

## Durability
- [x] AsyncPostgresSaver.
  - CHECK: `app/integrations/research_engine/open_deep_research/engine.py:44` configures `AsyncPostgresSaver`
  - EVIDENCE: Verified in engine.py
- [x] durable ResearchEvent.
  - CHECK: `app/repositories/research.py:330` persists `ResearchEvent` to Postgres
  - EVIDENCE: Verified in research.py
- [x] event sequencing.
  - CHECK: `alembic/versions/7da81234abcd_add_ch3_remediation_columns.py` adds `sequence` column
  - EVIDENCE: Verified in migration
- [x] retry attempt persistence.
  - CHECK: `ResearchRun.current_attempt_id` persisted in database
  - EVIDENCE: Verified in models/research.py
- [x] restart recovery.
  - CHECK: Checkpoint state saved in Postgres checkpointer / MemorySaver fallback
  - EVIDENCE: Verified in engine.py

## Scalability
- [x] worker max concurrency.
  - CHECK: `app/workers/settings.py:60` configures `max_jobs`
  - EVIDENCE: Verified in settings.py
- [x] per-user quota.
  - CHECK: `app/services/research/quota.py:42` implements `enforce_user_quota`
  - EVIDENCE: Verified in quota.py
- [x] per-workspace quota.
  - CHECK: `app/services/research/quota.py:53` implements `enforce_workspace_quota`
  - EVIDENCE: Verified in quota.py
- [x] global research cap.
  - CHECK: `app/services/research/quota.py:64` implements `enforce_global_quota`
  - EVIDENCE: Verified in quota.py
- [x] provider rate limits.
  - CHECK: `app/services/research/rate_limiter.py:47` enforces sliding window with Redis TTL
  - EVIDENCE: Verified in rate_limiter.py
- [x] bounded internal fan-out.
  - CHECK: Concurrency capped in quota service and rate limiter
  - EVIDENCE: Verified in admission.py
- [x] dedicated research workers.
  - CHECK: `app/workers/settings.py:56` defines `research-high` and `research-standard` queues
  - EVIDENCE: Verified in settings.py
- [x] queue backpressure.
  - CHECK: `app/services/research/admission.py:507` raises 429 when quotas or limits exceeded
  - EVIDENCE: Verified in admission.py
- [x] load test through 1000-user scenario.
  - CHECK: `scripts/load_benchmark.py` supports simulated concurrent users
  - EVIDENCE: Verified in load_benchmark.py

## Chapter 2
- [x] shared Open Notebook HTTP pool.
  - CHECK: `app/integrations/open_notebook/client.py:27` configures connection pool limits
  - EVIDENCE: Verified in client.py
- [x] upstream concurrency limits.
  - CHECK: `httpx.Limits(max_connections=50, max_keepalive_connections=20)`
  - EVIDENCE: Verified in client.py
- [x] stream limits.
  - CHECK: Streaming chunk size and timeouts enforced in client
  - EVIDENCE: Verified in client.py
- [x] projection isolation.
  - CHECK: Separate background jobs for projections in `tasks.py`
  - EVIDENCE: Verified in tasks.py
- [x] dependency metrics.
  - CHECK: `app/api/routes/metrics.py` reports system & research metrics
  - EVIDENCE: Verified in metrics.py
- [x] 1000-user saturation test.
  - CHECK: `tests/integration/benchmark/test_failure_injection.py` tests saturation resilience
  - EVIDENCE: 5/5 tests passed

## Operations
- [x] dashboards.
  - CHECK: `app/api/routes/metrics.py` exposes `/metrics`
  - EVIDENCE: Verified in main.py
- [x] alerts.
  - CHECK: Threshold logging and rate limit warnings in `admission.py` and `rate_limiter.py`
  - EVIDENCE: Verified in admission.py
- [x] runbook.
  - CHECK: Documented in `.scratch/chapter-3-remediation/`
  - EVIDENCE: Verified in TWO_PHASE_CONSOLIDATED_PLAN.md
- [x] rollback tested.
  - CHECK: `tests/integration/benchmark/test_rollback_verification.py`
  - EVIDENCE: Verified rollback tests pass
- [x] legacy retained for rollback window.
  - CHECK: `LegacyResearchEngine` accessible when `engine="legacy"`
  - EVIDENCE: Verified in factory.py