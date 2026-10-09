# ADR 0007: Conversational Turns, Explicit Study-Session Reports, and Sequential Engine Routing

## Status

Accepted (2026-10-09); revised 2026-10-10 (readiness gates, shared turn budget, claim-level citation validation).
- Partially supersedes [ADR 0005](0005-odr-only-research-runtime.md): the engine set, and decision 4's per-run report and
  candidate.
- Refines [ADR 0006](0006-storm-and-gpt-researcher-as-selectable-engines.md).
- Separates ADR 0002's production-capacity requirement from automatic-routing eligibility.

## Context

Every Research turn used to end in a formal report, and the engine was fixed per run. The first routing version kept
STORM and GPT-Researcher auto-routing hard-disabled pending a 1,000-user load test. As a result Auto mode was ODR-only in
practice. That conflated two separate questions:

1. Is an engine safe to choose for one bounded turn?
2. Has the deployment been validated at production scale?

## Decision

1. **Per-turn contract: ConversationalResponse + Evidence.**
   - Engines yield exactly one `turn_response` (`text`, `format`, `evidence_refs`, optional `details`) and may yield one
     `metrics` event before it.
   - Each engine's native control is used, with no rewrite call:
     - ODR: the response-style instruction travels in the user message that its final-answer prompt reads.
     - GPT-Researcher: `write_report(custom_prompt=...)`. A test runs the installed `generate_report` to verify it is used.
     - STORM: its own polish step writes a lead section (`# summary`). That lead, with the sources it cites, is the answer;
       the full article is kept as `details`. Only an article without a lead falls back to `format="article"`.
   - The worker stores the text as `assistant_message` and publishes `turn.completed` / `done` with the answer, evidence,
     the routing record, `answer_details` and worker timings.
2. **No automatic reports.** Ordinary turns create no `ResearchReport` and no candidate.
3. **StudyReportCompiler, on explicit request only.**
   - Owner and workspace authorization is enforced in the service.
   - It makes one bounded LLM call (with a timeout) that returns structured claims, each with a kind and the catalog
     numbers that support it.
   - Each claim's citations must exist in the session's catalog and be lexically relevant to the stored evidence text.
   - A finding that loses its support is rendered *[Unsupported by the collected evidence]*. Hypotheses, interpretations and
     calculations are labelled. A disagreement needs two sources.
   - References come from stored evidence. Recompiles create a new version. It never runs research and never promotes.
4. **Routing mode is separate from engine identity.**
   - `research_runs.routing_mode` is `auto` or `explicit`. In auto mode, `engine` is the engine that answered.
   - Every attempt row records the actual engine, preferred engine, routing mode, trigger, reason, outcome, timings, usage
     and usage quality.
5. **EngineRouter: one engine at a time.**
   - Intent routing:
     - simple → ODR `low`;
     - normal → ODR `balanced`;
     - deep → STORM directly if eligible;
     - broad → GPT-Researcher directly if eligible;
     - otherwise ODR (`deep` / `balanced`).
   - The deterministic assessment of an ODR answer checks:
     - unanswered sub-questions (term coverage plus anchor terms such as acronyms and names);
     - unresolved relationships;
     - engine-reported gaps;
     - uncited factual claims;
     - relevance and diversity of evidence domains (not the row count);
     - duplicated sources (by URL or content);
     - depth.
   - Escalation, at most once and sequentially:
     - depth, unanswered, unresolved or reported-gap failures go to STORM;
     - coverage, relevance, duplication or unsupported-claim failures go to GPT-Researcher.
   - Thresholds are calibrated against `tests/fixtures/routing/assessment_cases.json`.
6. **One shared execution policy per turn.**
   - Limits: a wall-clock deadline (`ROUTER_TURN_DEADLINE_S` = 1500, below the 1800 s ARQ `job_timeout`), at most two
     attempts, and a measured-token ceiling across attempts (`ROUTER_TURN_TOKEN_CEILING`).
   - Every per-engine timeout is capped by the remaining deadline, and a specialist needs at least
     `ROUTER_MIN_SPECIALIST_TIME_S` left.
   - ODR receives the remaining token allowance as its caps. Specialists use upstream-native "bounded" profiles: STORM
     runner arguments, and GPT-Researcher config keys.
   - Capacity: Redis-backed concurrency slots (`ROUTER_MAX_CONCURRENT_STORM` = 1, `..._GPT_RESEARCHER` = 2).
   - On timeout or cancellation the router cancels the attempt task, which runs the adapter cleanup (it terminates STORM's
     subprocess and cancels GPT-Researcher's task), and then calls `engine.cancel()`.
   - A periodic sweep finalizes runs that are provably dead (`RESEARCH_STALE_RUN_AFTER_S`).
7. **Readiness gates, independent per specialist.**
   - Gates: `ROUTER_AUTO_STORM` / `ROUTER_AUTO_GPT_RESEARCHER` = `auto` (default) or `off`.
   - With `auto`, the specialist is eligible when its runtime prerequisites pass: credentials, plus the STORM env with
     `knowledge_storm` importable, or `gpt_researcher` importable.
   - Contract, cancellation, bounded-execution and provenance prerequisites are verified by the test suite (see
     `docs/engine-readiness.md`).
   - **Production-capacity approval (1,000 users) is a separate, still-open state.** It does not block bounded,
     concurrency-limited automatic routing.

## Addendum (2026-10-10, reliability fixes)

- **Ground evidence.** Ground citations are resolved to canonical sources through this workspace's bindings only.
  Unresolvable citations are exposed (or fail the turn when nothing resolves), and are never presented as evidence.
- **Ground turns.** The streaming path honours the turn's source scope. Scopes are validated before a turn exists. Every
  failure and cancellation closes the turn exactly once, and provably dead turns are recovered instead of locking the
  conversation.
- **Deadlines.** The turn deadline is derived from the ARQ job timeout minus a finalize margin. A redelivered job for a
  terminal run is a no-op.
- **Engine setup.** An engine that fails to construct is an attempt failure, so the initial answer is kept.
- **Unmetered usage.** It is recorded as unmetered, never counted as zero.
- **Paper findings.** A finding counts as supported only with a verbatim, claim-matching quote from stored evidence;
  merely related citations are labelled.

## Consequences

- Auto mode genuinely routes across three engines; the UI and attempt rows show preferred vs actual engine and why.
- **Budgets:** only ODR has token-level enforcement. STORM and GPT-Researcher are bounded by wall-clock time, upstream
  configuration and concurrency, and the UI says so.
- **Latency is dominated by the free model gateway.** Measured: about 10–20 s per call even for "Say OK", and 9 ODR calls
  ≈ 180 s. The `low` profile and the token and time limits bound the work, but cannot make a slow gateway fast.
- **The deterministic checks are heuristics.** They are calibrated on fixtures, not on labelled production answers.
  Lexical citation relevance cannot prove entailment.
