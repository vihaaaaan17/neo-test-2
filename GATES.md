# GATES — Ticket 01: Ground + Streaming Fabric

## Gates

- [ ] G1: `resolve_ground_source_scope` fails closed on foreign source IDs (rejects if any provided UUID does not exist in workspace)
  - CHECK: `python -m pytest tests/unit/test_ground_context_scope.py -v`
  - EXPECT: all passed
  - EVIDENCE: pending

- [ ] G2: `OpenNotebookGroundEngine` maps canonical `source_scope` to Open Notebook source IDs and passes `context_config.sources` to Open Notebook `/api/chat/context`, failing closed with 422 if explicit scope has zero valid mappings
  - CHECK: `python -m pytest tests/unit/test_ground_engine_source_scope.py -v`
  - EXPECT: all passed
  - EVIDENCE: pending

- [ ] G3: `OpenNotebookClient.chat_stream()` yields incremental token chunks rather than a single full string
  - CHECK: `python -m pytest tests/unit/test_open_notebook_client_stream.py -v`
  - EXPECT: all passed
  - EVIDENCE: pending

- [ ] G4: `_get_or_create_conversation_session` uses row-level locking on `OpenNotebookConversationBinding` to prevent concurrent duplicate session creation
  - CHECK: `python -m pytest tests/unit/test_ground_session_binding.py -v`
  - EXPECT: all passed
  - EVIDENCE: pending

- [ ] G5: `format_sse_event` outputs standard `id: <sequence>\nevent: <type>\ndata: <json>\n\n`
  - CHECK: `python -m pytest tests/unit/test_sse_wire_format.py -v`
  - EXPECT: all passed
  - EVIDENCE: pending

- [ ] G6: Unified SSE stream generator in `ChatService` and `list_turn_events` route accepts `Last-Event-ID`, replays historical PostgreSQL events, deduplicates by sequence, and streams live Redis events
  - CHECK: `python -m pytest tests/integration/chat/test_events.py -k test_ground_turn_sse_streaming -v`
  - EXPECT: all passed
  - EVIDENCE: pending

- [ ] G7: End-to-end Ground turn execution and streaming tests pass with zero regressions
  - CHECK: `python -m pytest tests/e2e/test_ground_research_ground.py tests/test_ground_mode_api.py -v`
  - EXPECT: all passed
  - EVIDENCE: pending