# Engine Readiness

Four distinct states per engine. Each state needs evidence; a later state never follows from an earlier one automatically.

| State | Meaning |
|---|---|
| **Integrated** | A thin adapter over the real upstream runtime satisfies the engine contract in tests |
| **Available for manual testing** | Runs through the API/worker when selected explicitly (`routing_mode: "explicit"`) |
| **Eligible for automatic routing** | Gate `auto` (default) + runtime prerequisites pass + capacity slot free; bounded by the Turn Budget |
| **Validated for production workload** | Load-tested at the 1,000-user target with acceptable latency, cost and error rates (ADR 0002) |

## Current status (2026-10-10)

| Engine | Integrated | Manual testing | Automatic routing | Production workload |
|---|---|---|---|---|
| Open Deep Research | yes | yes (live) | yes, default engine; live `low` / `balanced` / `deep` runs | **not validated** (no load test) |
| STORM | yes | yes (live explicit run + live cancellation) | yes, gate `ROUTER_AUTO_STORM=auto`, max 1 concurrent; live direct route and live escalation target | **not validated** (no load test) |
| GPT-Researcher | yes | yes | yes, gate `ROUTER_AUTO_GPT_RESEARCHER=auto`, max 2 concurrent; live direct route | **not validated** (no load test) |

The live evidence (2026-10-10, through the API and worker) is in `docs/live-verification.md`. The 1,000-user load test has
not been run. A live *escalation to GPT-Researcher* has not been observed yet; it is covered by router tests.

## Prerequisites for automatic routing (and where they are verified)

| Prerequisite | ODR | STORM | GPT-Researcher | Verified by |
|---|---|---|---|---|
| Normalized answer/evidence contract (`turn_response`) | yes | yes (lead section answer, article in `details`) | yes (`custom_prompt`) | `tests/unit/integrations/research_engine/test_engine_contract.py`, `test_adapter_output_contracts.py` |
| Evidence/provenance through Neosis (`record_sources_as_evidence` / `neosis_web_search`) | yes | yes | yes | contract tests, `tests/integration/research/test_study_session_workflow.py` |
| Bounded execution | token/call caps + profile | wall clock + `bounded` runner args | wall clock + `bounded` config keys | `test_engine_router.py` (shared deadline/token ceiling), adapter tests |
| Cancellation stops the underlying work | task cancel | subprocess terminated | upstream task cancelled | `test_storm_engine_integration.py`, `test_engine_router.py::test_router_timeout_terminates_a_real_storm_subprocess`, GPT-R adapter tests |
| Failure handling (raise, no terminal status) | yes | yes | yes | contract tests |
| Runtime prerequisites (checked at routing time, cached 5 min) | LLM + Tavily keys | + `venv-storm` with `knowledge_storm` | + `gpt_researcher` importable | `router.check_prerequisites` |

A gate set to `off`, a missing prerequisite or a full capacity slot all leave the turn on ODR. The routing record says which
of the three happened (`readiness[].state`, `escalation.blocked`).

## Budget profiles (upstream-native knobs only)

- **ODR**: `low` / `balanced` / `deep` profiles of `max_concurrent_research_units`, `max_researcher_iterations` and
  `max_react_tool_calls`, plus the UsageTracker call/token/search caps. These caps are further limited by the remaining turn
  token ceiling.
- **STORM**: `bounded` (default for routing) / `standard`, set through STORMWikiRunnerArguments: `max_conv_turn`,
  `max_perspective`, `max_search_queries_per_turn`, `search_top_k`, `retrieve_top_k`, `max_thread_num`.
- **GPT-Researcher**: `bounded` (default) / `standard`, set through its config keys: `MAX_ITERATIONS`,
  `MAX_SEARCH_RESULTS_PER_QUERY`, `MAX_SCRAPER_WORKERS`, `MAX_SUBTOPICS`, `TOTAL_WORDS`, `SMART_TOKEN_LIMIT`.

Usage quality differs by engine:

| Engine | Tokens | Cost |
|---|---|---|
| ODR | measured | unavailable |
| STORM | measured (LiteLLM usage) | unavailable |
| GPT-Researcher | unavailable | estimated |

## Timeout hierarchy (effective values, verified from the running worker's startup log on 2026-10-10)

```
ARQ job_timeout (ARQ_JOB_TIMEOUT_S)                   1800 s   ARQ kills the job after this
  > turn deadline (effective_turn_deadline_s)         1500 s   = min(ROUTER_TURN_DEADLINE_S, ARQ_JOB_TIMEOUT_S - ROUTER_FINALIZE_MARGIN_S)
    + finalize margin (ROUTER_FINALIZE_MARGIN_S)        180 s   persist outcome, release resources, emit the one terminal event
  each engine attempt = min(engine timeout, remaining turn deadline)
    ODR 600 s, STORM 900 s, GPT-Researcher 900 s; a specialist needs >= ROUTER_MIN_SPECIALIST_TIME_S (180 s) left
Ground turns: Open Notebook client timeouts (30 s / 120 s for ask); a Ground turn running > GROUND_TURN_STALE_AFTER_S (600 s)
  with no live task is recovered on the next submission.
Research runs pending/running > RESEARCH_STALE_RUN_AFTER_S (7200 s) are finalized by the 10-minute sweep.
```

The worker logs this hierarchy at startup and logs a warning if a too-long `ROUTER_TURN_DEADLINE_S` was clipped. A
redelivered ARQ job (`max_tries=3`, e.g. after a worker crash) for a run that is already terminal is a no-op.

## Limits per engine and across the turn

| Limit | Scope | ODR | STORM | GPT-Researcher |
|---|---|---|---|---|
| Wall-clock deadline (turn) | whole turn, shared, never reset | enforced | enforced | enforced |
| Per-attempt timeout | attempt, capped by remaining deadline | enforced | enforced (subprocess terminated) | enforced (upstream task cancelled) |
| Max attempts | whole turn (`1 + ROUTER_MAX_SPECIALIST_ESCALATIONS`, default 2) | enforced | enforced | enforced |
| Measured-token ceiling | whole turn (`ROUTER_TURN_TOKEN_CEILING`) | enforced mid-run (UsageTracker caps = min(profile, remaining)) | **not enforceable** (no token control; usage reported after the run, and "unavailable" when the gateway omits it) | **not enforceable** (only an estimated cost after the run) |
| Upstream output-size limits | attempt | `*_model_max_tokens` per profile | `bounded` runner args (perspectives, turns, queries, threads) | `bounded` config (`SMART_TOKEN_LIMIT`, `TOTAL_WORDS`, iterations, results, scrapers) |
| Deployment-wide concurrency | across all turns | quotas only | 1 slot (`ROUTER_MAX_CONCURRENT_STORM`) | 2 slots (`ROUTER_MAX_CONCURRENT_GPT_RESEARCHER`) |

There is **no strict cross-engine token budget**: only measured tokens (ODR, STORM when the gateway reports them) count
toward the ceiling. An attempt without measured usage is recorded in `routing.budget.unmetered_attempts`, and the turn's
`token_accounting` is then `incomplete`. It is never counted as zero usage. Note that `research_options.token_budget` sizes
the research *context*; it is not an execution budget.

## Configuration (`app/core/config.py`, override in `.env`)

```
ROUTER_AUTO_STORM=auto                 # auto | off
ROUTER_AUTO_GPT_RESEARCHER=auto        # auto | off
ROUTER_MAX_CONCURRENT_STORM=1
ROUTER_MAX_CONCURRENT_GPT_RESEARCHER=2
ROUTER_MAX_SPECIALIST_ESCALATIONS=1
ROUTER_TURN_TOKEN_CEILING=1200000
ARQ_JOB_TIMEOUT_S=1800
ROUTER_FINALIZE_MARGIN_S=180
ROUTER_TURN_DEADLINE_S=1500            # clipped to ARQ_JOB_TIMEOUT_S - ROUTER_FINALIZE_MARGIN_S
ROUTER_MIN_SPECIALIST_TIME_S=180
ROUTER_TIMEOUT_ODR_S=600
ROUTER_TIMEOUT_STORM_S=900
ROUTER_TIMEOUT_GPT_RESEARCHER_S=900
ROUTER_STORM_PROFILE=bounded
ROUTER_GPT_RESEARCHER_PROFILE=bounded
RESEARCH_STALE_RUN_AFTER_S=7200
GROUND_TURN_STALE_AFTER_S=600
```

