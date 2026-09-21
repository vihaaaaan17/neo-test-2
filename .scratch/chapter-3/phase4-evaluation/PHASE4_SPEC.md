# NeosisLM Chapter 3 — Phase 4 Specification

## Problem Statement

The new ResearchEngine (Open Deep Research adapter) has been implemented (Phase 3), but it is not yet the production-primary path. We need to conclusively measure, validate, harden, cut over, and operationalize the new engine to ensure it meets quality, cost, latency, reliability, and isolation requirements without changing the fundamental Chapter 3 architecture.

## Solution

We will execute an evaluation and operationalization phase (Phase 4). We will establish a benchmark corpus, freeze the legacy baseline, and evaluate the new engine deterministically against it. We will strictly audit provenance, test workspace isolation, establish hard cost/latency budgets, optimize the new engine to fit within those budgets, and build an operational runbook. Finally, we will cut over via a centralized feature flag and deprecate the legacy engine.

## User Stories

1. As an engineer, I want a frozen benchmark corpus, so that I can reproduce research runs reliably without hallucinated data.
2. As an engineer, I want a legacy baseline, so that I have a stable anchor to compare new engine performance against.
3. As a user, I want the new engine to meet or exceed legacy quality, so that my research results are actually better, not just different.
4. As an auditor, I want a deterministic provenance audit script, so that I can verify every citation marker maps securely back through the artifacts and evidence to the original source.
5. As a system operator, I want strict workspace isolation tests, so that I can guarantee no cross-workspace data leakage occurs during parallel execution.
6. As a business owner, I want explicit cost and latency ceilings derived from the baseline, so that the new engine does not bankrupt the product or stall indefinitely.
7. As an engineer, I want the Open Deep Research adapter to be optimized for concurrency and depth, so that it fits within the cost and latency ceilings.
8. As a system operator, I want automated rollback testing and a configuration feature flag, so that I can safely fail back to the legacy engine if the new engine encounters a critical production issue.
9. As an SRE, I want simulated worker and upstream timeout tests, so that I know partial runs resolve safely and canonical state is preserved.
10. As an SRE, I want concrete dashboard queries and structured logging documented in a Runbook, so that I can monitor the health of the new ResearchEngine in production.
11. As a developer, I want the legacy engine marked as deprecated, so that it is explicitly removed from active development, pending physical deletion in a later cleanup phase.

## Implementation Decisions

- **Benchmark Corpus**: 20-30 representative JSONL prompts (`tests/fixtures/benchmark/corpus.jsonl`).
- **Quality Gates**: LLM-judge for subjective report quality + deterministic citation checking.
- **Provenance Audit**: Complete chain verification: `Report -> Claim -> Artifact -> Evidence -> Source -> Task -> Run -> Workspace`. Any fabricated links fail the build.
- **Cost/Latency Ceilings**: Empirical limits based on baseline measurements, enforced via the `UsageTracker`.
- **Optimization**: We will tune ODR concurrency and prompt depth to fit the budget. We will not change its core search capabilities.
- **Rollback Mechanism**: Centralized via `ResearchEngineFactory` using `ACTIVE_RESEARCH_ENGINE` feature flag.
- **Observability**: Structured JSON logging (`logger.info`) with `run_id`, `cost`, `duration`, etc. No new third-party metrics SDKs.
- **Legacy Deprecation**: `@deprecated` decorators and `warnings.warn`. Physical deletion is out of scope for Chapter 3.

## Testing Decisions

- **Offline Shadow Benchmark**: Shadow evaluations will be run offline via `benchmark.py` against the static corpus to avoid mutating production Knowledge Memory.
- **Workspace Isolation**: `test_workspace_isolation.py` will run parallel jobs and actively assert authorization rejections on cross-workspace access.
- **Reliability Tests**: `test_rollback.py` will validate that toggling the engine flag works mid-stream or between runs.

## Out of Scope

- Physical deletion of the legacy `ResearchModeOrchestrator` (deferred to a post-Chapter 3 cleanup phase).
- Introduction of Datadog/Prometheus SDKs into the application codebase.
- Changing the fundamental Phase 3 architecture or rebuilding upstream research logic.
- Building a billing subsystem.

## Further Notes

- The legacy path remains available through the approved rollback window.
- The new engine will be cut over only when all Phase 4 Exit Gates are passed.
