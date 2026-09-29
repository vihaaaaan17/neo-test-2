# Ticket 01: Phase 3 Schema, Models, Migration & Repositories

## Summary
Extend existing models (`ResearchArtifact`, `Workspace`, `WorkspaceCommit`, `ResearchRun`), generate Alembic migration, and implement repository methods for candidate lifecycle, manifest management, and atomic timeline epoch handling.

## Scope & Changes
1. **`app/models/research.py`**:
   - Extend `ResearchArtifact`:
     - `promotion_status`: `String`, default `pending_review` (or `not_promotable` for non-candidate artifacts), nullable=False.
     - `reviewed_by`: `UUID(as_uuid=True)`, nullable=True.
     - `reviewed_at`: `DateTime(timezone=True)`, nullable=True.
     - `review_reason`: `String`, nullable=True.
     - `promoted_target_type`: `String`, nullable=True (`knowledge_memory`, `output_graph`, `scratchpad_entry`, `claim_finding`).
     - `promoted_target_id`: `UUID(as_uuid=True)`, nullable=True.
     - `verification_status`: `String`, nullable=True (`verified`, `unverified`, `failed`).
     - `verification_reason`: `JSONB`, nullable=True.
     - `verification_metadata`: `JSONB`, nullable=True.
   - Extend `ResearchRun`:
     - `base_commit_id`: `UUID(as_uuid=True)`, ForeignKey("workspace_commits.commit_id", ondelete="SET NULL"), nullable=True.

2. **`app/models/workspace.py`**:
   - Extend `Workspace`:
     - `timeline_epoch`: `Integer`, default 1, nullable=False.
   - Extend `WorkspaceCommit`:
     - `manifest`: `JSONB`, default dict, nullable=False.
     - (Retain `active_knowledge_ids` for backwards compatibility).

3. **Alembic Migration**:
   - Create migration `add_phase3_promotion_lifecycle_and_timeline_epoch.py`.
   - Add new columns to `research_artifacts`, `research_runs`, `workspaces`, `workspace_commits`.

4. **`app/repositories/research.py`**:
   - `list_candidates_by_status(workspace_id, status, run_id=None)`
   - `get_candidate_for_review(workspace_id, artifact_id)`
   - `set_candidate_decision(workspace_id, artifact_id, status, reviewed_by, review_reason=None)`
   - `link_candidate_target(workspace_id, artifact_id, target_type, target_id)`
   - `set_candidate_verification(workspace_id, artifact_id, status, reason, metadata=None)`

5. **`app/repositories/workspace.py`**:
   - `create_commit_with_manifest(workspace_id, parent_id, active_knowledge_ids, manifest)`
   - `rollback_workspace_atomic(workspace_id, commit_id, owner_id)`:
     - `SELECT ... FOR UPDATE` on `Workspace`.
     - Verify commit belongs to workspace.
     - `timeline_epoch = timeline_epoch + 1`.
     - `active_commit_id = commit_id`.
     - Commit and return updated workspace and new epoch.
   - `verify_timeline_epoch(workspace_id, expected_epoch)` -> `bool`.

## Verification Gates
- [ ] Models load and schema matches PostgreSQL definitions.
- [ ] Alembic migration applies cleanly.
- [ ] Unit tests for `ResearchRepository` candidate querying, decision transitions, and target linking pass.
- [ ] Unit tests for `WorkspaceRepository` atomic rollback and epoch increment pass.
