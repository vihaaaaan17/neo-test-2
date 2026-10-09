# Chapter 6, Phase 2: Cost-Aware Sequential Engine Routing

## Objective

`Worker → EngineRouter → one active adapter → upstream engine`. The router picks the cheapest adequate engine and escalates
at most once, sequentially, for a measurable reason.

## Current state (inspected 2026-10-09)

- `ResearchRun.engine` is `NOT NULL` and is a concrete engine name. Admission validates it against `SUPPORTED_ENGINES`.
- ADR 0005 says "ODR only"; ADR 0006 added STORM and GPT-Researcher as explicit engines. ADR 0002's load-test condition is
  unmet, and nothing has been load tested.
- ODR enforces call/token caps through `UsageTracker` (defaults 100 calls / 1M input tokens). The UI's "token budget" sizes
  the research context; it is not an execution cap. STORM and GPT-Researcher record usage only after the fact.

## Decisions

1. **Routing mode is separate from engine identity.** A new `research_runs.routing_mode` column holds `auto` or `explicit`, and
   `engine` becomes nullable.
   - Explicit runs carry the requested engine.
   - Auto runs carry `NULL` until an attempt answers; then `engine` is set to the engine that answered.
   - API: `research_options.routing_mode` (default `auto` when no engine is given, `explicit` when one is). `"auto"` is never
     accepted as an engine name.
2. **Attempts are auditable.** A new table `research_engine_attempts` stores one row per attempt: sequence, engine, trigger
   (`initial`, `intent`, `escalation`, `fallback`), reason, status, timing, tokens, cost, evidence count, assessment metrics
   and error. `current_attempt_id` points to the latest attempt.
3. **EngineRouter** (`app/integrations/research_engine/router.py`) implements `ResearchEngine`, so the worker stays
   engine-agnostic.
   - **Intent classification** is deterministic:
     - `simple` routes to ODR with the `low` profile.
     - `normal` routes to ODR with the `balanced` profile.
     - `deep` routes to STORM if it is eligible, otherwise ODR `deep`.
     - `broad` routes to GPT-Researcher if it is eligible, otherwise ODR `balanced`.
   - **Sufficiency assessment** is deterministic and runs on ODR answers. It checks answer words, unsupported-claim markers,
     unique source domains and the duplicate-URL ratio.
     - Empty answers, insufficient depth and unsupported claims escalate to STORM.
     - Low source coverage and excessive duplication escalate to GPT-Researcher.
     - No LLM evaluator.
   - **Bounds:**
     - at most one specialist escalation and at most two attempts;
     - per-engine timeouts;
     - escalation skipped when the turn's token ceiling is used up;
     - no `gather` or `TaskGroup`: attempts are awaited one after another.
   - **Failure handling:**
     - If a specialist fails after ODR answered, the ODR answer is kept.
     - If a directly routed specialist fails, the router falls back to ODR once.
     - If ODR itself fails, or cancellation or a budget stop happens, the error propagates to the worker.
4. **Readiness gates.** `ROUTER_AUTO_STORM_ENABLED` and `ROUTER_AUTO_GPT_RESEARCHER_ENABLED` both default to `False`, because
   there is no load-test evidence (ADR 0002) and no mid-run budget. Availability is also checked (`venv-storm` exists, the
   `gpt_researcher` module is importable). When a gate blocks an escalation, the block and its reason are recorded. Explicit
   overrides still work for testing.
5. **ODR budget profiles** use ODR's native configuration (`max_concurrent_research_units`, `max_researcher_iterations`,
   `max_react_tool_calls`) plus the `UsageTracker` caps. Only ODR is reported as `budget_enforced`.
6. **UI:** "Auto (recommended)" is the default, with explicit overrides. After each run the UI shows the answering engine,
   every attempt, the escalation reason and whether the budget was enforced.

## Docs

ADR 0007 (routing and conversational contract); ADR 0005 and ADR 0006 status notes; `docs/CONTEXT.md`;
`docs/engine-readiness.md`; the API contract note.
