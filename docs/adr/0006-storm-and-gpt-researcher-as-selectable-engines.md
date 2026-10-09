# ADR 0006: STORM and GPT-Researcher as Selectable Research Engines

## Status

Accepted (2026-10-08). Supersedes [ADR 0002](0002-storm-formal-deferral.md) (the STORM deferral) and completes the engine
set started in [ADR 0005](0005-odr-only-research-runtime.md).

## Context

ADR 0002 deferred STORM because it would sit *beside* Open Deep Research (ODR) as a second supervisor inside one run, with
duplicated planning, unbounded fan-out and evidence that bypassed Neosis provenance. ADR 0005 removed the invented research
machinery and made the worker the single owner of terminal state. That removes the premise of the deferral: STORM and
GPT-Researcher are not used as sub-components of ODR. Each is a **complete upstream engine, selected per run**, and exactly one
engine executes a given `ResearchRun`.

## Decision

1. **Three engines, one allow-list.** `SUPPORTED_ENGINES = ("open_deep_research", "storm", "gpt_researcher")`. Admission
   rejects anything else with `422 unsupported_research_engine`; the factory has one branch per engine as a backstop.
   `ACTIVE_RESEARCH_ENGINE` is only the default. `STORM_ENABLED` is removed.
2. **Thin adapters over the real upstream runtimes.** Each adapter passes the objective and provider settings, forwards
   upstream progress as Neosis progress events, routes collected sources into evidence persistence, and yields exactly one
   `final_report`. No planner, loop, retriever registry or prompt of our own was added.
   - `GPTResearcherEngine` calls `GPTResearcher.conduct_research()` / `write_report()` in-process, configured through its JSON
     config file and the OpenAI-compatible environment exported once by `app.core.config`.
   - `StormResearchEngine` runs `STORMWikiRunner` in a **separate virtual environment** (`venv-storm`) through a small runner
     script and a JSON-line protocol, because `knowledge-storm` pins `dspy_ai==2.4.9` (`openai<2`) which cannot coexist with the
     application's `openai>=2`. The runner imports no `app` code.
3. **Provenance.** Both adapters persist sources through `record_sources_as_evidence`
   (`app/integrations/research_engine/evidence.py`): scoped to the run and workspace, deduplicated by URL, stored as
   `unresolved_external` with title and URL as provenance. Research output never becomes Ground evidence; the report is stored by
   `ResearchService.finalize_report` as a `pending_review` memory candidate like any other engine.
4. **Single-supervisor semantics.** One engine per run, and the worker owns terminal state exactly as in ADR 0005. Adapters raise
   on failure; cancellation cancels the worker's child task, which cancels the upstream task (GPT-Researcher) or terminates the
   STORM process. Admission applies the LLM and search rate limits to every engine.
5. **`workspaces.research_engine` is constrained** to the three names by a check constraint (migration `5c1e7a9d2b30`).

## Consequences

- **Resource governance (partly open).** Concurrency quotas and rate limits apply per run to every engine. Mid-run token
  budgets are enforced only for ODR; STORM and GPT-Researcher report usage after the fact (STORM from its LM call history,
  GPT-Researcher from its cost counter) and have no mid-run budget cut-off. STORM additionally spawns a process per run with its
  own thread pool (`max_thread_num`, default 3) and downloads a local ranking model on first use.
- **Neither engine takes Neosis research context or prior evidence.** Both accept only a topic/query.
- **Load testing is NOT done.** Nothing here has been exercised under the 1,000-user target; ADR 0002's load-test condition
  remains open and is recorded as a known follow-up. Verification so far: contract tests over all three adapters, and one real
  run per engine against the live provider (`tests/smoke/test_real_provider.py`, opt-in).
- **Operational cost.** STORM needs `venv-storm` (`requirements-storm.txt`, `STORM_PYTHON` to override). The main environment
  carries the GPT-Researcher dependency set; `pip check` reports one metadata-only conflict (`unstructured` declares `wrapt>=2.1.1`
  while `aiobotocore` needs `wrapt<2`; `wrapt` is pinned to 1.x).
- **Known gaps carried over:** no research graph output; coarse progress events.
