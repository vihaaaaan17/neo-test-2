# GATES — Ticket 01: Ground + Streaming Fabric

## Gates

- [x] G1: `resolve_ground_source_scope` fails closed on foreign source IDs
  - CHECK: `python -m pytest tests/unit/test_ground_context_scope.py -v`
  - EVIDENCE: PASSED (2026-09-29)

- [x] G2: `OpenNotebookGroundEngine` maps canonical `source_scope` to Open Notebook source IDs, passes `context_config.sources`, fails closed with 422 on zero valid mappings
  - CHECK: `python -m pytest tests/unit/test_ground_engine_source_scope.py -v`
  - EVIDENCE: PASSED (2026-09-29)

- [x] G3: `OpenNotebookClient.chat_stream()` yields incremental token chunks, accepts `context_config` kwarg
  - CHECK: `python -m pytest tests/unit/test_open_notebook_client_stream.py -v`
  - EVIDENCE: PASSED (2026-09-29)

- [x] G4: `_get_or_create_conversation_session` uses `with_for_update()` row-level locking
  - CHECK: `python -m pytest tests/unit/test_ground_session_binding.py -v`
  - EVIDENCE: PASSED (2026-09-29)

- [x] G5: `format_sse_event` outputs `id: <sequence>\nevent: <type>\ndata: <json>\n\n`
  - CHECK: `python -m pytest tests/unit/test_sse_wire_format.py -v`
  - EVIDENCE: 3 passed in 5.85s (2026-09-29)

- [x] G6: Unified SSE generator in `ChatService.stream_turn_events` accepts `after_sequence`, subscribes Redis pubsub before DB read, replays with `id:` headers, deduplicates by sequence, exits on terminal events. `list_turn_events` reads `Last-Event-ID` header as cursor, auth-gates streaming path.
  - CHECK: `python -m pytest tests/integration/chat/test_events.py -v`
  - EVIDENCE: 7 passed in 13.26s (2026-09-29)
  - CHECK2: `python -m pytest tests/e2e/test_unified_turn_stream.py -v`
  - EVIDENCE2: 3 passed (2026-09-29)

- [x] G7: E2E Ground/Research/Ground isolation + zero graph-sync invariant
  - CHECK: `python -m pytest tests/e2e/test_ground_research_ground.py -v`
  - EVIDENCE: 3 passed in 4.84s (2026-09-29)

## All 7 gates GREEN ✅ — Ticket 01 COMPLETE
Commit: c7cb5a2 (main)