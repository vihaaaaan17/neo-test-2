# GATES.md — Ticket 01: Ground + Streaming Fabric

Ticket: `01-ground-streaming-fabric.md`
Objective: Source-scope enforcement, true Open Notebook streaming, session rehydration,
SSE IDs/replay/live bridge, Redis transport.

---

## Gate Summary

| Gate | Description | Status | Evidence |
|------|-------------|--------|----------|
| G1   | Source scope fail-closed (HTTP 422 on zero mappings) | ✅ PASSED | `tests/unit/test_ground_context_scope.py` |
| G2   | Ground engine maps UUIDs, passes `context_config`, fails closed | ✅ PASSED | `tests/unit/test_ground_engine_source_scope.py` |
| G3   | `chat_stream` yields incremental token events, accepts `context_config` | ✅ PASSED | `tests/unit/test_open_notebook_client_stream.py` |
| G4   | Session binding uses `with_for_update()` for locking | ✅ PASSED | `tests/unit/test_ground_session_binding.py` |
| G5   | SSE wire format emits `id: <sequence>` lines | ✅ PASSED | `tests/unit/test_sse_wire_format.py` (3/3) |
| G6   | Unified SSE stream generator: replay + Redis pubsub bridge + Last-Event-ID | ✅ PASSED | `tests/integration/chat/test_events.py` (7/7) + `tests/e2e/test_unified_turn_stream.py` (3/3) |
| G7   | E2E: Ground/Research/Ground isolation + zero graph-sync invariant | ✅ PASSED | `tests/e2e/test_ground_research_ground.py` (3/3) |

All 7 gates GREEN. ✅

---

## Run Log

### G1 — Source Scope Fail-Closed
```
Command: python -m pytest tests/unit/test_ground_context_scope.py -v
Result:  PASSED (3 tests)
Date:    2026-09-29
```

### G2 — Ground Engine Source Scope Mapping
```
Command: python -m pytest tests/unit/test_ground_engine_source_scope.py -v
Result:  PASSED
Date:    2026-09-29
```

### G3 — OpenNotebook Client Incremental Streaming
```
Command: python -m pytest tests/unit/test_open_notebook_client_stream.py -v
Result:  PASSED
Date:    2026-09-29
```

### G4 — Session Binding Row Lock
```
Command: python -m pytest tests/unit/test_ground_session_binding.py -v
Result:  PASSED
Date:    2026-09-29
```

### G5 — SSE Wire Format `id:` Header
```
Command: python -m pytest tests/unit/test_sse_wire_format.py -v
Result:  3 passed in 5.85s
Date:    2026-09-29
```

### G6 — Unified SSE Stream Generator (Last-Event-ID, Redis bridge, dedup)
```
Commands:
  python -m pytest tests/unit/test_sse_wire_format.py tests/e2e/test_unified_turn_stream.py -v
  Result:  6 passed in 5.01s

  python -m pytest tests/integration/chat/test_events.py -v
  Result:  7 passed in 13.26s
Date:    2026-09-29
```

Key assertions verified:
- `Last-Event-ID: 2` header -> only events with sequence > 2 replayed
- Every SSE frame carries `id: <sequence>` line
- Redis pubsub subscribed before DB read (no missed-event race)
- Redis unavailability (no localhost:6379) degrades gracefully in <1s
- Terminal events (`done`, `error`, `cancelled`) close stream immediately
- Auth gate via `get_turn_events()` enforced before streaming

### G7 — E2E Ground/Research/Ground Isolation
```
Command: python -m pytest tests/e2e/test_ground_research_ground.py -v
Result:  3 passed in 4.84s
Date:    2026-09-29
```

Assertions verified:
- Research text/reports 100% excluded from Ground context
- `sync_knowledge_to_graph_job` never enqueued from Ground turns
- Source scope strictly applied to Turn 3 (Ground after Research)
