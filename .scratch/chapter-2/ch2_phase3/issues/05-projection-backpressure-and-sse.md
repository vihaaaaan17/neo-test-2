# 05 - Projection Backpressure & SSE

## Objective
Protect Open Notebook from bulk-upload concurrency floods and implement Server-Sent Events (SSE) for the Ask workflow.

## Requirements
1. **Projection Backpressure**:
   - Introduce a dedicated Arq queue (or worker concurrency limit) specifically for `project_to_open_notebook_job`.
   - Update the job to catch HTTP 429 and `JobExecutionFailed` with explicit backoff settings.

2. **SSE Streaming Route**:
   - Implement `POST /api/v1/workspaces/{workspace_id}/ask/stream` in `workspaces.py`.
   - Connect to Open Notebook's stream (if supported) using `httpx`.
   - Map Open Notebook's internal tokens/events into Neosis's standard `event: ... \n data: ...` structure.
   - Do not leak internal Open Notebook event names to the client.

## Acceptance Criteria
- Batch uploading 1000 files does not DDOS Open Notebook.
- Streaming route yields standard Neosis events to the frontend.
