# 01 - Provenance Hardening & Error Translation

## Objective
Enforce strict zero-evidence rejection in Ground Mode and safely translate Open Notebook HTTP errors to Neosis domain errors without leaking internal details.

## Requirements
1. **Provenance Status**:
   - Update `app/integrations/open_notebook/ground_engine.py` and `citation_mapper.py`.
   - If `AskResponse` yields `evidence=[]` after mapping, it must raise a `422 Unprocessable Entity` (or appropriate Ground rejection), preventing the answer from being saved to Neosis Memory as grounded fact.
   - If evidence is partial, attach `provenance_status="partial"` to the API response metadata but return 200 OK.

2. **Error Translation**:
   - Update `OpenNotebookClient` to catch `httpx.HTTPStatusError`.
   - Map `400` -> `ground_validation_error` (HTTP 400).
   - Map `5xx` / timeouts -> `ground_dependency_unavailable` (HTTP 503) or `ground_execution_failed` (HTTP 502).
   - Sanitize the user-facing detail message completely, but log the raw upstream error using standard Python logging.

## Acceptance Criteria
- Answers with zero mapped canonical evidence throw a 422.
- No raw SurrealDB or Python errors from Open Notebook leak to the API consumer.
