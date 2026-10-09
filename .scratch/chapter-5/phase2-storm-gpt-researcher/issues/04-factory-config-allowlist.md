# 04: Factory, Allow-list, and Configuration

**What to build:**
Enable exactly three upstream engines through the existing allow-list and factory, with minimal explicit configuration.

**Blocked by:** 02, 03

**Status:** done (2026-10-08)

- [x] `SUPPORTED_ENGINES = ("open_deep_research", "storm", "gpt_researcher")`; admission accepts all three and rejects everything else (422).
- [x] `ResearchEngineFactory.get_engine` has one branch per engine instantiating only the matching thin adapter; unknown names raise deterministically;
      no branch may instantiate a custom orchestrator, retriever registry or alternate research loop.
- [x] `app/core/config.py`: keep `ACTIVE_RESEARCH_ENGINE = "open_deep_research"`; retire `STORM_ENABLED` as a deferral flag
      (replace with the minimum availability/provider settings the upstream packages require); no large engine-config framework.
- [x] Confirm `run_research_agent_job` contains no engine-specific branches.
- [x] `ui/app.py`: engine selection reflects the supported engines (hardcoded list, same approach as Phase 1).
- [x] Optional: add the DB check constraint on `workspaces.research_engine` in a new migration.
- [x] Factory/admission unit tests for all three engines and for rejection of unknown names.

## Implementation notes
- Allow-list, factory branches, rate limits for every engine (previously ODR-only), `STORM_ENABLED` removed, UI engine selectbox, check-constraint migration `5c1e7a9d2b30` (migration-only, not on the model). `run_research_agent_job` has no engine-specific branches (only the engine name in events).
