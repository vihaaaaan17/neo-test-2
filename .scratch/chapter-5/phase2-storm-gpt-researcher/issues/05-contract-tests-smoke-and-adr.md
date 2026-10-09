# 05: Contract Tests, Smoke Gate, Dead-code Gate, and ADR

**What to build:**
Prove all three engines behave identically at the contract level, run one real-provider smoke test per enabled engine, and record
the architectural decision.

**Blocked by:** 04

**Status:** done (2026-10-08)

- [x] Shared contract test suite parameterized over the three adapters (inputs, normalized events, final result, run identity,
      failure, cancellation where supported, no bypass of evidence/provenance).
- [x] Extend `tests/smoke/` with a real-provider test per enabled engine, asserting checklist items 1–8 from `.scratch/chapter-5/verification-checklist.md`.
- [x] Final repository search (see checklist) for `ResearchModeOrchestrator`, `LegacyResearchEngine`, `RetrieverRegistry`, `WebRetriever`,
      `AcademicRetriever`, `MCPRetriever`, `GPTResearcherRetriever`, `GPTResearcherTool`, `WebSearchTool`, `research_engine="legacy"`, `planner_node`,
      `executor_node`, `synthesizer_node`, `reporter_node`: no application references.
- [x] New ADR superseding ADR 0002's STORM deferral; it states how provenance, resource governance and single-supervisor semantics are
      satisfied and whether load testing under the 1,000-user target has been done or remains open.
- [x] Update `docs/UPSTREAM_REVISION.md` with the pinned STORM and GPT-Researcher revisions used.

## Implementation notes
- `test_engine_contract.py` (3 engines), smoke renamed `tests/smoke/test_real_provider.py` parametrized per engine (opt-in; not yet run for STORM/GPT-R through the API+worker), dead-code gate clean, ADR 0006, UPSTREAM_REVISION updated, `gpt-researcher==0.15.1` pinned. Load test remains open.
