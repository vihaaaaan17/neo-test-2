# 04 - Deletion Tombstones & Reconciliation

## Objective
Ensure guaranteed eventual consistency for Open Notebook resource cleanup without blocking Neosis's canonical deletion paths.

## Requirements
1. **Tombstone Model**:
   - Create `DeletionTombstone` in `app/models/open_notebook_binding.py`. Fields: `tombstone_id`, `resource_type` (workspace/source), `open_notebook_id`, `status` (pending, completed, failed), `attempt_count`, `last_attempt`.

2. **Deletion Flow Update**:
   - Update `app/api/routes/workspaces.py` (for workspace deletion) and `delete_source` logic.
   - When a canonical item is deleted, insert a `DeletionTombstone` atomically with the deletion transaction.
   - Enqueue a cleanup job pointing to the tombstone ID.

3. **Reconciliation Worker**:
   - Implement an Arq periodic task (cron) or explicit job to sweep for `status='pending'` tombstones and repeatedly attempt deletion against Open Notebook.
   - Set limits on retry cadence (e.g. exponential backoff on the tombstone).

## Acceptance Criteria
- Workspaces and sources delete instantly in Neosis even if Open Notebook is down.
- Tombstones are processed and resolved once Open Notebook recovers.
