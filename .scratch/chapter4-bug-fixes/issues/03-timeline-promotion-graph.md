# 03: Timeline + Promotion + Graph

**What to build:**
Fix timeline epoch fencing, candidate eligibility, and Output Knowledge Graph projection integrity in the existing Chapter 4 implementation. Persist `timeline_epoch` directly on `ResearchRun` at admission time as an immutable baseline via an Alembic migration. Enforce timeline epoch fencing across all worker durable writes (status updates, report creation, artifact creation, graph sync) and in `PromotionService.accept_candidate()`, aborting operations from stale epochs (`aborted_by_timeline_fence`). Restrict promotion candidates strictly to `memory_candidate` and `graph_candidate`, rejecting unsupported types (`hypothesis_candidate`, `claim_candidate`, `finding_candidate`) with `HTTP 400 invalid_candidate_type`. Validate candidate payloads strictly against Pydantic schemas. Enqueue background jobs (`sync_knowledge_to_graph_job`, `project_output_graph_job`) strictly *after* the PostgreSQL transaction commits. Validate Output KG topology (non-empty node IDs, valid edge endpoints) before projection, tag projected graph subgraphs with `commit_id` and `workspace_id`, and reject independent projection jobs that lack active-commit authority.

**Blocked by:** None (can start immediately)

**Status:** completed

- [x] `ResearchRun` schema and Alembic migration include `timeline_epoch`.
- [x] Worker write operations and `PromotionService.accept_candidate()` verify the active workspace timeline epoch and abort if the epoch has advanced.
- [x] Only `memory_candidate` and `graph_candidate` can be accepted; unsupported candidate types return `HTTP 400 invalid_candidate_type`.
- [x] Candidate payloads are validated against Pydantic schemas prior to acceptance.
- [x] Background projection jobs are enqueued strictly post-transaction commit.
- [x] Malformed graph topologies are rejected before projection; projected subgraphs carry `commit_id` and `workspace_id`.
