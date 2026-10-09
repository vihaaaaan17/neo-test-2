# Phase 2 — STORM + GPT-Researcher as True Upstream Engines

Parent: `.scratch/chapter-5/spec.md`. Starts only after Phase 1 is complete and its smoke gate has passed.

## Objective

Expose STORM and GPT-Researcher as top-level engines using only their upstream runtimes. Neosis adds thin adapters that
conform to the same engine contract as ODR; no Neosis planner, executor or synthesizer is written around them.

## Engine contract (set by Phase 1, not redefined here)

- `ResearchEngine.astream_events(run_id, workspace_id, objective, research_context=None, ...)` yields progress dicts and
  exactly one `{"status": "final_report", "report": str}`; failures are raised exceptions.
- `ResearchEngine.cancel()` exists; adapters implement it only where the upstream runtime supports cancellation.
- The worker owns terminal state, persistence, finalization and the single terminal event.
- Evidence and provenance enter Neosis only through Neosis evidence persistence (no research-derived material becomes Ground evidence).
- `resolve_llm_provider()` is the provider-resolution path; prefer the upstream's own configuration mechanism over env mutation.

## Rules

1. Before writing any adapter, inspect the installed `knowledge-storm` / `gpt-researcher` packages and use their actual public API.
   Do not code against an assumed API.
2. Do not reproduce upstream algorithms (STORM: question decomposition, perspective generation, multi-pass research, citation
   gathering, article drafting; GPT-Researcher: planning, crawling, report workflow).
3. GPT-Researcher is a full engine, not a search tool inside ODR. Do not patch its internal LLM implementation unless a narrow
   provider-compatibility boundary requires it.
4. ADR 0002 (STORM deferral) is superseded by a new ADR in this phase, which must address its objections: provenance integrity
   (via the existing evidence ACL), resource governance/budgets, and single-supervisor semantics (STORM runs as a selectable engine,
   not alongside ODR). Load testing under the 1,000-user target is called out explicitly as verified or still open.

## Implementation decisions

- Files: `app/integrations/research_engine/storm/engine.py` (`StormResearchEngine`) and
  `app/integrations/research_engine/gpt_researcher/engine.py` (`GPTResearcherEngine`).
- `SUPPORTED_ENGINES` becomes `("open_deep_research", "storm", "gpt_researcher")`; factory branches instantiate only the matching adapter;
  unknown names still fail deterministically.
- `STORM_ENABLED` is retired as an architecture-status flag; any configuration added is the minimum the upstream packages require.
- The worker stays engine-agnostic; no engine-specific branches in `run_research_agent_job`.
- Optional (after both adapters work): DB check constraint on `workspaces.research_engine`.

## Testing decisions

- Contract tests per adapter: accepts the same inputs, produces normalized progress events and one `final_report`, preserves
  workspace/run identity, raises on failure, handles cancellation where supported, does not bypass the evidence/provenance boundary.
  Files: `tests/unit/integrations/research_engine/test_{odr,storm,gpt_researcher}_engine_integration.py`.
- One real-provider smoke test per enabled engine, mirroring the Phase 1 gate (checklist items 1–8).

## Acceptance criteria

- Engine status: ODR active (primary), STORM active behind a thin adapter, GPT-Researcher active behind a thin adapter.
- Final repository search for the Phase 1 symbol list returns no application hits; `GPTResearcherRetriever` and `GPTResearcherTool` stay deleted.
- Engine selection deterministic; failure/cancellation never leaves a stuck run; no duplicate terminal events.
