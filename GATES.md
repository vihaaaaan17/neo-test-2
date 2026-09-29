# GATES — Ticket 05: Production Hardening + Contracts + E2E

## Gates

- [x] G1: Research metrics are populated with real runtime execution values (tokens, tool call counts, latency) and all timestamps use `timezone.utc`
  - CHECK: `python -m pytest tests/unit/research/test_research_metrics_hardening.py -v`
  - EXPECT: passed
  - EVIDENCE: 4/4 passed (emit_metrics_utc_and_structured_tokens, emit_metrics_scalar_tokens_fallback, track_helpers_and_utc_normalization, get_observability_dashboard_data_aggregation)

- [x] G2: Checkpointer lifecycle and reconciliation scripts are safely scoped without leaking cross-workspace state
  - CHECK: `python -m pytest tests/unit/research/test_checkpointer_and_reconciliation_scoping.py -v`
  - EXPECT: passed
  - EVIDENCE: 3/3 passed (test_odr_checkpointer_thread_id_scoping, test_reconcile_open_notebook_bindings_workspace_isolation, test_link_historical_research_runs_strict_workspace_scoping)

- [x] G3: Frozen handoff documents (`chapter4-api-contract.md`, `chapter4-event-catalog.md`, `chapter4-state-model.md`, `chapter4-ui-handoff.md`) match canonical implementation
  - CHECK: manual audit of contracts against implementation
  - EXPECT: synchronized
  - EVIDENCE: Candidate promotion API (Section 8), CandidateType ('memory_candidate' | 'graph_candidate'), ResearchRunResponse, and aborted_by_timeline_fence terminal status synchronized across all 4 documents.

- [x] G4: End-to-end tests verify Ground source containment, SSE reconnection, timeline fencing, and rollback visibility
  - CHECK: `python -m pytest tests/e2e/test_chapter4_hardening_e2e.py -v`
  - EXPECT: passed
  - EVIDENCE: 4/4 passed (test_e2e_ground_source_containment, test_e2e_sse_reconnection_and_sequence_replay, test_e2e_timeline_epoch_fence_worker_abort, test_e2e_rollback_visibility_and_epoch_quarantine)

- [x] G5: Complete test suite passes with 100% success
  - CHECK: `python -m pytest tests/unit/ tests/e2e/ -q`
  - EXPECT: passed
  - EVIDENCE: 234 passed, 0 failed in 45.74s

## Status
Passed