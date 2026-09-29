# GATES — Ticket 03: Timeline + Promotion + Graph

## Gates

- [x] G1: `ResearchRun` schema and Alembic migration include `timeline_epoch`
  - CHECK: `python -m pytest tests/unit/research/test_timeline_promotion_graph.py -k test_research_run_schema_and_migration -v`
  - EXPECT: 1 passed
  - EVIDENCE: Passed. `ResearchRun.timeline_epoch` defined as `Column(Integer, default=1, nullable=False)` in `app/models/research.py`, exposed in `ResearchRunResponse` schema, resolved at admission in `app/services/research/admission.py` and `app/repositories/research.py`, and added in migration `alembic/versions/f7a8b9c0d1e2_add_phase3_promotion_lifecycle_and_timeline_epoch.py` preserving DAG linearity.

- [x] G2: Worker write operations and `PromotionService.accept_candidate()` verify active workspace timeline epoch and abort if advanced (`aborted_by_timeline_fence`)
  - CHECK: `python -m pytest tests/unit/research/test_timeline_promotion_graph.py -k test_timeline_epoch_fencing -v`
  - EXPECT: passed
  - EVIDENCE: Passed (2/2 tests passed: `test_timeline_epoch_fencing_promotion_service` and `test_timeline_epoch_fencing_workers`). Stale epochs trigger `TimelineEpochFencedError("aborted_by_timeline_fence")` mapped to HTTP 409 Conflict, and worker jobs abort without overwriting status with `failed`.

- [x] G3: Only `memory_candidate` and `graph_candidate` can be accepted; unsupported candidate types return `HTTP 400 invalid_candidate_type`
  - CHECK: `python -m pytest tests/unit/research/test_timeline_promotion_graph.py -k test_unsupported_candidate_types_rejected -v`
  - EXPECT: passed
  - EVIDENCE: Passed (4/4 tests passed for `hypothesis_candidate`, `claim_candidate`, `finding_candidate`, and `unknown_type`). `InvalidCandidateTypeError` mapped to HTTP 400 with detail `invalid_candidate_type`.

- [x] G4: Candidate payloads are validated against Pydantic schemas prior to acceptance
  - CHECK: `python -m pytest tests/unit/research/test_timeline_promotion_graph.py -k test_candidate_payload_pydantic_validation -v`
  - EXPECT: passed
  - EVIDENCE: Passed. `MemoryCandidatePayload` and `GraphCandidatePayload` enforced in `PromotionService.accept_candidate()`; invalid/empty payloads raise `InvalidPayloadError`.

- [x] G5: Background projection jobs (`sync_knowledge_to_graph_job`, `project_output_graph_job`) are enqueued strictly post-transaction commit
  - CHECK: `python -m pytest tests/unit/research/test_timeline_promotion_graph.py -k test_background_projection_post_commit -v`
  - EXPECT: passed
  - EVIDENCE: Passed. `session.commit()` and `session.refresh()` precede `arq_pool.enqueue_job()` in `PromotionService.accept_candidate()`, guaranteeing data durability prior to job dispatch.

- [x] G6: Malformed graph topologies rejected; projected subgraphs carry `commit_id` and `workspace_id`, reject independent projection lacking active-commit authority
  - CHECK: `python -m pytest tests/unit/research/test_timeline_promotion_graph.py -k test_graph_projection_topology_and_authority -v`
  - EXPECT: passed
  - EVIDENCE: Passed. Topology validation in `project_output_graph` and worker reject empty nodes and broken edges with `malformed_graph_topology`; subgraphs tag `commit_id` and `workspace_id`; projection jobs lacking active-commit authority are rejected with `lacks_active_commit_authority`.

## Status
Completed