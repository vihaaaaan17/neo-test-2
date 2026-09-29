# Ticket 04: Timeline Epoch Rollback Fence, Commit Manifest & End-to-End Verification

## Summary
Enforce the PostgreSQL `timeline_epoch` concurrency fence, implement workspace commit manifest snapshotting and restoration, build comprehensive unit and integration test suites, and execute regression validation.

## Scope & Changes
1. **Workspace Rollback Epoch Concurrency Fence**:
   - In `app/api/routes/workspaces.py` (`rollback_workspace` endpoint):
     - Update rollback endpoint to use `WorkspaceRepository.rollback_workspace_atomic(workspace_id, commit_id, current_user_id)`.
     - Rollback acquires row-level lock (`FOR UPDATE`), verifies commit belongs to workspace, atomically increments `timeline_epoch = timeline_epoch + 1`, updates `active_commit_id = commit_id`, and emits `workspace.rollback.created`.
   - In `app/workers/tasks.py`:
     - When research job starts, read `expected_epoch = workspace.timeline_epoch`.
     - Before committing durable state or candidate finalization, check `workspace.timeline_epoch == expected_epoch`.
     - If epoch has advanced (rollback occurred while job was running): abort durable mutations, record status `aborted_by_timeline_fence`, preserve historical execution logs/reports, and emit `workspace.rollback.fence_triggered`.

2. **Commit Manifest Snapshotting & Restoration**:
   - In `app/api/routes/workspaces.py` (`create_commit` endpoint):
     - Assemble full manifest: `active_knowledge_ids`, `accepted_artifact_ids`, `output_graph_version`, `active_hypothesis_ids`, `scratchpad_checkpoint`, `conversation_checkpoint`, `base_research_run_ids`, `schema_version = 1`.
     - Persist `WorkspaceCommit` with `manifest` JSONB.

3. **Phase 3 Test Suites**:
   - `tests/unit/research/test_promotion.py`:
     - Test candidate creation with `pending_review` status.
     - Test individual accept (`memory_candidate` -> single `KnowledgeMemory`).
     - Test individual reject (`promotion_status = 'rejected'`, audit fields populated, no durable target).
     - Test double acceptance idempotency.
     - Test dual-target independence (accept memory, reject graph; or vice versa).
     - Test cross-workspace candidate acceptance rejection (403/fail-closed).
   - `tests/unit/research/test_verification.py`:
     - Test deterministic arithmetic verification (+, -, *, /, **, %, //, functions).
     - Test resource bounds (AST depth > 10, length > 500, exponent > 10, magnitude > 1e15).
     - Test safety constraints (reject `eval`, `__import__`, attribute access, syntax errors).
     - Test unverified/failed calculation behavior (candidate remains in `pending_review` with failure reason).
   - `tests/unit/research/test_provenance.py`:
     - Test typed `ProvenanceRef` resolution across 7 entity types.
     - Test cross-workspace provenance rejection: candidate from Workspace A referencing evidence from Workspace B fails closed.
     - Test missing provenance entity handling.
   - `tests/unit/workspace/test_rollback_epoch.py`:
     - Test rollback increments `timeline_epoch` atomically.
     - Test stale worker attempting promotion or mutation with older epoch is blocked.
     - Test historical research runs, evidence, and reports remain intact after rollback.
     - Test valid post-rollback promotion with new epoch succeeds.

4. **Codebase Graph Update**:
   - Run `graphify update .` to keep knowledge graph current.

## Verification Gates
- [ ] All Phase 3 unit tests pass without errors.
- [ ] Entire regression test suite (`pytest tests/unit/ -v`) passes cleanly.
- [ ] Knowledge graph updated via `graphify update .`.
- [ ] Full gate ledger written to `.scratch/chapter-4/GATES_PHASE_3.md`.
