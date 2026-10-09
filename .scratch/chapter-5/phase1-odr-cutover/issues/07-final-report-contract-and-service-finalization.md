# 07: `final_report` Event, Service Finalization, and Graph-Candidate Removal

**What to build:**
The engine hands the final report to the worker as data; the worker persists it through one engine-agnostic
`ResearchService` method. All `final_graph` / `graph_candidate` creation on the ODR path is removed (ODR never produces
a graph; this was legacy-only).

**Blocked by:** 06

**Status:** done (2026-10-07)

- [x] In `OpenDeepResearchEngine.astream_events`, on `final_report_generation` yield exactly
      `{"status": "final_report", "report": <markdown>}`; remove `create_report`, `memory_candidate` and `graph_candidate`
      creation, the engine's own timeline-fence check, and the `final_graph` fields from the synthesizing event.
- [x] Add `ResearchService.finalize_report(workspace_id, run_id, objective, report)` (or equivalent) in
      `app/services/research/service.py`: creates the `ResearchReport` and the `pending_review` `memory_candidate` artifact with the
      same payload shape as today (`evidence_refs`, `source_refs`, provenance v2, `proposed_memory_type="research_memory"`,
      `metadata.source="odr"` unless a neutral value is needed — keep existing values).
- [x] Worker: consume the `final_report` event (do not publish or bridge it as a progress/chat event); persist via the service
      before the existing "assistant summary from latest report" lookup; keep candidate normalization as is.
- [x] Worker: remove `final_graph` capture and the "ensure graph_candidate exists" block. Leave promotion/projection code untouched.
- [x] `ui/app.py`: check whether anything reads the old `summary` field of the synthesizing event or a `final_graph` payload;
      adjust only what is necessary and note findings in the PR.
- [x] Record "research graph generation" as a Chapter 5 product gap in `.scratch/chapter-5/spec.md` (already listed) and
      in the PR description.
- [x] Unit tests: engine yields `final_report` (and no persistence side effects); service creates report + candidate;
      worker persists exactly once and does not publish the report as a progress event.
- [x] Suite shows no new failures versus the ticket-01 baseline.

## Notes (2026-10-07, implemented together with 06 and 08)

- Engine yields `synthesizing` (message only) then `{"status": "final_report", "report": ...}`; it writes nothing and has no fence check.
- `ResearchService.finalize_report(workspace_id, run_id, objective, report)` creates the report and the `pending_review` `memory_candidate` (same payload shape as before).
  `metadata.source` is now `run.engine` (`open_deep_research`) instead of the hardcoded `"odr"`; nothing in the repo read the old value.
  `ResearchService.__init__` made `memory_router` / `graph_repo` optional so finalization needs only the repository.
- Worker: captures `final_report` (never published/bridged), persists it after the timeline-fence check and before the lifecycle transition, and no longer captures `final_graph`
  or creates a `graph_candidate`. Promotion/projection code is untouched. "Research graph generation" remains the recorded Chapter 5 product gap.
- `ui/app.py` does not read `summary`, `final_graph` or the synthesizing payload, so no UI change was needed.
- Test updates: `test_odr_adapter_candidate_emission.py` rewritten for the new contract; mock engines in `test_research_worker_streaming.py`, `test_research_worker_bridge.py`
  and `test_phase3_end_to_end.py` now yield `final_report` (the integration test now exercises the real worker persistence against Postgres).
