# 03 - Circuit Breaking & Telemetry

## Objective
Protect the Neosis API thread pool from Open Notebook outages via a Circuit Breaker and inject correlation headers for observability.

## Requirements
1. **Circuit Breaker**:
   - Implement a lightweight, in-memory circuit breaker inside `OpenNotebookClient` (e.g. `pybreaker` or a custom state machine).
   - Trip the breaker on consecutive `ConnectTimeout`, `ReadTimeout`, or `5xx` errors.
   - When OPEN, short-circuit API requests immediately with 503.

2. **Correlation Headers**:
   - Ensure the `httpx.AsyncClient` passes standard OpenTelemetry context if available.
   - Explicitly inject custom headers `X-Neosis-Run-ID`, `X-Neosis-Request-ID`, and `X-Neosis-Workspace-ID` in every external request payload.

## Acceptance Criteria
- Simulating a full downstream outage immediately triggers 503s after the threshold, without tying up connections.
- Headers are present on upstream requests.
