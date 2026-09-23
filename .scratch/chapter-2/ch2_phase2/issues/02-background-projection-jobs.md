# 02 - Background Projection Jobs

## Objective
Implement the asynchronous projection and cleanup jobs for Open Notebook to mirror Neosis canonical state changes safely.

## Requirements
1. **Source Projection (`project_to_open_notebook_job`)**:
   - Enqueue in parallel to `parse_and_chunk_job` in `upload_file_to_workspace`.
   - Use `OpenNotebookRepository` to claim projection state atomically (`PENDING` -> `PROJECTING`).
   - Download the canonical snapshot from S3.
   - Project to Open Notebook using `OpenNotebookClient.upload_source`.
   - Upon success, update binding to `ACTIVE`. If a new snapshot is projected, enqueue deletion for the old snapshot's projection.
   - Handle failures gracefully (`FAILED` or `RECONCILIATION_REQUIRED`).

2. **Source Deletion (`delete_open_notebook_source_job`)**:
   - Enqueue when a canonical source is deleted in Neosis.
   - Call Open Notebook DELETE API for the bound `open_notebook_source_id`.
   - Idempotent: must handle case where upstream source is already deleted or binding doesn't exist.

3. **Workspace Deletion (`delete_open_notebook_workspace_job`)**:
   - Enqueue when a workspace is deleted.
   - Call Open Notebook notebook deletion API with `delete_exclusive_sources = True`.

## Acceptance Criteria
- Async jobs implemented and registered in `app/workers/tasks.py`.
- Duplicate dispatch for projection is safely aborted via atomic claims.
- Projection handles transient errors.
- Integration tests verify the end-to-end enqueueing and upstream API calls.
