# 06: Move Context Formatting and Evidence/Context Loading Out of the ODR Adapter

**What to build:**
The ODR adapter should receive plain data and do no database reads for context. The worker resolves prior evidence and
`research_context`; the formatter becomes an engine-agnostic service function; the adapter still prepends the formatted block
to the ODR objective message.

**Blocked by:** 04, 05

**Status:** done (2026-10-07)

- [x] Create `app/services/research/context.py` with `format_research_context(research_context) -> str`, moved verbatim from
      `OpenDeepResearchEngine._format_research_context` (behaviour unchanged, including the "RESEARCH CONTEXT AND WORKING STATE" block).
- [x] Move prior-evidence lookup (last ≤10 items, 1,500-char snippets, "PREVIOUS RESEARCH FINDINGS" block) into a service/worker helper;
      the worker passes the resulting text to the engine as part of the objective or an explicit parameter.
- [x] Move the "load `research_context` from the turn's `context_version`" fallback into the worker (it already loads the run/turn).
- [x] `OpenDeepResearchEngine.astream_events` no longer imports `ResearchRun`, `ConversationTurn` or `list_evidence_for_run`
      for context purposes; usage checkpointing stays as is (Q11).
- [x] Keep ADR 0004 behaviour: the adapter prepends the block to the initial user message; ODR graph/prompts untouched.
- [x] Unit tests: `format_research_context` golden output (reuse existing assertions from the ODR integration tests), retry
      evidence injection bounds, worker passes context when `research_context` is not supplied directly.
- [x] Suite shows no new failures versus the ticket-01 baseline.

## Notes (2026-10-07, implemented together with 07 and 08)

- New `app/services/research/context.py`: `format_research_context` (moved verbatim) and `build_prior_evidence_context` (last 10 items, 1,500-char snippets).
- The worker now resolves `prior_evidence_context` and (when not supplied) the turn's `research_context`, and passes both to `engine.astream_events` as plain data
  (`prior_evidence_context` is a keyword on the adapter; the abstract interface already accepts `**kwargs`). Both lookups are non-fatal (warning only).
- The adapter no longer reads `ResearchRun`/`ConversationTurn`/evidence for context. It still opens sessions for usage checkpoints (unchanged, per Q11).
