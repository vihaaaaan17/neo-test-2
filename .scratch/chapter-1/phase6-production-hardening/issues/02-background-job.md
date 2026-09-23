# 02: Create export_workspace_job worker

**What to build:** An asynchronous background task using `arq` that executes the workspace export off the main API thread. When the export is complete, the worker broadcasts the resulting signed download URL to a Redis pub/sub channel so the frontend can receive it.

**Blocked by:** 01: Build WorkspaceExportService

**Status:** ready-for-agent

- [ ] `export_workspace_job(ctx, workspace_id, owner_id)` added to `app/workers/tasks.py`.
- [ ] Job invokes `WorkspaceExportService` and handles potential exceptions.
- [ ] Job publishes a message to the Redis channel `export:<workspace_id>` containing the presigned download URL.
- [ ] Worker configuration is updated to register the new job.
