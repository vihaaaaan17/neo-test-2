# 04 - Ask Workflow Facade & Cutover Verification

## Objective
Update the Neosis `/ask` endpoint to route traffic to the correct engine based on feature flags, and expose Open Notebook processing metrics.

## Requirements
1. **`GroundEngineRouter` Facade**:
   - In `app/api/routes/workspaces.py` (or a dedicated factory), instantiate either `GroundModeOrchestrator` or `OpenNotebookGroundEngine` based on `OPEN_NOTEBOOK_ENABLED`.
   - Ensure the legacy code remains perfectly isolated and functional when the flag is false.

2. **Projection Status Metrics**:
   - Enhance the `AskResponse` metadata or related `/status` endpoints to expose the number of active/pending source projections, so the UI can indicate indexing progress. (Query the `OpenNotebookSourceBinding` table).
   - Do not block `/ask` queries while sources are pending. Query against the currently indexed Open Notebook notebook.

3. **Lifecycle & Happy-Path Verification**:
   - Write an integration test suite validating the full end-to-end flow: Workspace Binding -> Source Upload -> Arq projection -> `/ask` execution via Open Notebook -> Citation mapping.
   - Verify that partial failures and timeouts behave correctly.

## Acceptance Criteria
- `/ask` endpoint safely delegates to the appropriate engine.
- Processing status is queryable.
- E2E Happy Path passes against the pinned `open_notebook` container.
- Phase 2 exit criteria are fully satisfied.
