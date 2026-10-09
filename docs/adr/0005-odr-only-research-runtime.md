# ADR 0005: Open Deep Research Is the Only Research Runtime

## Status

Accepted (2026-10-07); **partially superseded**: the engine set by [ADR 0006](0006-storm-and-gpt-researcher-as-selectable-engines.md)
and the per-run `final_report` / automatic report + candidate (decision 4) and "ODR is the only engine" by
[ADR 0007](0007-conversational-turns-and-engine-routing.md) (automatic three-engine routing).
The worker-owns-terminal-state, thin-adapter and single-provider decisions remain in force. Originally: supersedes only the "GPT Researcher is integrated strictly as a capability retriever via the Neosis ACL"
clause of [ADR 0002](0002-storm-formal-deferral.md). ADR 0002's STORM deferral was superseded by [ADR 0006](0006-storm-and-gpt-researcher-as-selectable-engines.md), which adds STORM and GPT-Researcher as selectable engines (so "ODR is the only supported engine" below describes the Phase 1 state).

## Context

NeosisLM's research mode was meant to be a thin compatibility layer over upstream research engines. The repository had
grown invented research machinery beside the real Open Deep Research (ODR) integration:

- a custom `ResearchModeOrchestrator` / `LegacyResearchEngine` with its own planner, executor, synthesizer and prompts;
- a custom retriever framework (`app/services/research/retrievers/`) and a `GPTResearcherTool` / `GPTResearcherRetriever` bridge
  that the ODR path never called;
- a legacy `WebSearchTool` injected into every engine but used only by the legacy one.

The ODR adapter also performed product work (report/candidate persistence, DB lookups, environment mutation), and both the
engine and the worker emitted terminal states, which could duplicate terminal events and skip finalization on cancel.

## Decision

1. **ODR is the only supported engine.** `SUPPORTED_ENGINES = ("open_deep_research",)` is the single allow-list used by
   admission and the factory. Unsupported engines are rejected at admission with `422 unsupported_research_engine` before a
   `ResearchRun` exists; the factory raises `ResearchEngineSetupError` as a backstop. `ACTIVE_RESEARCH_ENGINE` is only a default
   and never overrides a persisted `ResearchRun.engine`. Existing `legacy` workspaces were migrated to ODR.
2. **Invented research machinery is removed**, not relocated: the legacy engine/orchestrator, `WebSearchTool`, the retriever
   framework, `GPTResearcherRetriever` and `GPTResearcherTool`. ODR's upstream graph and prompts are used as vendored.
3. **The adapter is a boundary, not a product layer.** `OpenDeepResearchEngine` builds the ODR config, injects the bounded
   Neosis research context (formatted by the engine-agnostic `app/services/research/context.py`), translates upstream node
   updates into progress events, and yields exactly one `final_report` event. It persists no reports or candidates, reads no
   context from the database and writes no environment variables.
4. **The worker is the terminal-state owner.** Engines signal failure by raising. The worker maps
   `ResearchBudgetExceeded` → `partial`, cancellation → `cancelled`, other exceptions → `failed`, a missing report → `failed`
   (`engine_finished_without_report`), and a report → `completed` after persisting it through `ResearchService.finalize_report`
   (report + `pending_review` memory candidate). It publishes exactly one terminal event and treats an already-terminal run
   (for example cancelled by the API) as done. Cancellation stops a worker-owned child task so finalization still runs.
5. **One provider-resolution path.** `resolve_llm_provider()` in `app/core/config.py` decides key, base URL and model for every
   caller; `app.core.config` is the only place that exports the OpenAI-compatible environment variables upstream ODR reads.

## Consequences

- **Positive:** one research execution plane; no duplicated planner/search/synthesis logic; deterministic engine selection;
  single, testable terminal-state semantics; adapters for future engines conform to a small contract.
- **Negative / known gaps:**
  - ODR does not produce an output graph, so research runs no longer create `graph_candidate` artifacts. Promotion and projection
    remain in place; research graph generation is recorded as a Chapter 5 product gap.
  - ODR progress events are coarse (top-level nodes only); finer granularity (`subgraphs=True`) is a later UX improvement.
  - `legacy_baseline.json` is kept as immutable history and no longer represents a runnable engine.
- **Verification:** an offline deterministic harness runs the real ODR graph with fake model/search
  (`tests/harness/odr_offline.py`), and an opt-in real-provider smoke gate (`tests/smoke/test_real_provider.py`) checks
  completion, event stream, provenance, report persistence, Ground isolation, deterministic engine selection, cancellation and
  exactly-one terminal state/event.
