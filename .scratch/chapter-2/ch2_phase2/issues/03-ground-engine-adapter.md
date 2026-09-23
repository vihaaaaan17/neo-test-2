# 03 - Ground Engine Adapter & Citation Translation

## Objective
Implement the Open Notebook Ground Engine adapter that translates the Neosis Ask request to the Open Notebook search API and normalizes the response.

## Requirements
1. **`OpenNotebookGroundEngine`**:
   - Create `app/integrations/open_notebook/ground_engine.py`.
   - Implement the `.run()` contract (matching `GroundModeOrchestrator.run`).
   - Call the Open Notebook Ask/Search API using the notebook bound to the `workspace_id`.
   - If the API is unavailable or synthesis fails partially, raise a clean exception (no legacy fallback, no local synthesis).

2. **Citation Translation (`citation_mapper.py`)**:
   - Receive the raw Open Notebook IDs in the response.
   - Use `OpenNotebookSourceBinding` to map upstream source IDs back to canonical Neosis `source_id`/`snapshot_id`s.
   - If an upstream ID cannot be mapped or a precise locator is missing, set `provenance_status = "partial"`, omit the raw ON ID from the final canonical response, but retain it in telemetry/warnings.
   - Format the final `AskResponse` cleanly using canonical Neosis `evidence` UUIDs.

## Acceptance Criteria
- `OpenNotebookGroundEngine` correctly queries Open Notebook.
- Citations are strictly mapped back to canonical UUIDs.
- Partial provenance gracefully omits unmapped IDs and logs warnings.
- Upstream failures throw proper 503/504 errors.
