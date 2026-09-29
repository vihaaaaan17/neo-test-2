# 03: Unified SSE Token Streaming & Reconnect Event Replay

**What to build:**  
The real-time streaming transport and historical event replay layer for conversation turns. When a client submits a turn with `stream=true`, Ground turns yield incremental tokens and citations inline, while Research turns bridge live Redis Pub/Sub events into standard Server-Sent Events. All emitted events are durably persisted to PostgreSQL so that clients reconnecting after network drops can replay missed events via `GET /turns/{turn_id}/events?after_sequence={n}`.

**Blocked by:** 02: Unified Turn Execution Engine (Ground & Research)

**Status:** ready-for-agent

### Acceptance Criteria
- [ ] `ChatEvent` repository and event service in `app/services/chat/events.py` provide atomic event persistence and monotonic sequence allocation per turn.
- [ ] Submitting `POST /turns?stream=true` with `mode: "ground"` returns an HTTP `text/event-stream` delivering live tokens, strategy status, citations, and a terminal `done` event.
- [ ] Submitting `POST /turns?stream=true` with `mode: "research"` subscribes to the Redis Pub/Sub channel `research_events:{run_id}` and transforms engine progress events into standard turn SSE events (`event: progress`, `event: token`, `event: done`).
- [ ] Disconnecting the client from an active SSE stream does NOT interrupt backend execution; turn state and research jobs continue durably in the background.
- [ ] Replay endpoint `GET /api/v1/workspaces/{workspace_id}/conversations/{conversation_id}/turns/{turn_id}/events` retrieves historical events ordered by sequence, with optional `after_sequence` filtering.
- [ ] All SSE events follow the standard format: `event: <type>\ndata: <json_payload>\n\n`.
- [ ] Integration tests in `tests/integration/chat/test_events.py` verify live Ground token streaming, Research Redis event bridging, client disconnect resilience, and historical replay.
