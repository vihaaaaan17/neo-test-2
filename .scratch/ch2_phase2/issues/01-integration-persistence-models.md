# 01 - Integration Persistence Models

## Objective
Implement the dedicated integration binding models to isolate Open Notebook identity from Neosis canonical models.

## Requirements
1. **Workspace Binding**:
   - Create `OpenNotebookWorkspaceBinding` model in `app/models/open_notebook_binding.py`.
   - Fields: `workspace_id` (FK to `workspaces`, PK), `open_notebook_notebook_id` (String), `status`, `created_at`, `updated_at`.
   - Ensure a 1:1 mapping (a single Neosis workspace maps to exactly one Open Notebook notebook).

2. **Source Binding**:
   - Create `OpenNotebookSourceBinding` model in `app/models/open_notebook_binding.py`.
   - Fields: `source_id` (UUID), `snapshot_id` (UUID), `open_notebook_source_id` (String), `checksum_sha256` (String), `projection_status` (String), `projected_at` (DateTime), `error_meta` (JSONB).
   - Primary Key/Unique Constraint: `(source_id, snapshot_id)`.
   - Projection Statuses: `PENDING`, `PROJECTING`, `ACTIVE`, `FAILED`, `RECONCILIATION_REQUIRED`.

3. **Repository**:
   - Create `OpenNotebookRepository` in `app/repositories/open_notebook.py`.
   - Implement atomic lookup/claim methods for `OpenNotebookSourceBinding` to manage the projection state machine safely and prevent duplicate projections.

## Acceptance Criteria
- Alembic migration generated and applied for the new models.
- Repository provides atomic claims for the projection state machine.
- Unit tests verify the unique constraints and state transitions.
