# GATES — Ticket 05: API Contract Freeze, Deprecation Cleanup & Chapter 5 Frontend Handoff

## Gates

- [x] G1: Unit test validates OpenAPI schema generates cleanly (`/openapi.json` returns 200, no internal ODR/LangGraph/SurrealDB symbols in path/component names)
  - CHECK: `python -m pytest tests/unit/test_openapi_contract.py -v`
  - EXPECT: all passed (6 passed)
  - EVIDENCE: 6 passed in 12.02s (`test_openapi_schema_generates_without_error`, `test_no_internal_engine_symbols_in_schema`, `test_canonical_schemas_present_in_components`, `test_canonical_api_paths_present`, `test_output_graph_schema_present`, `test_research_run_schema_present`).

- [x] G2: Unit test verifies RFC 8288 Deprecation + Link headers on all legacy routes (`/ask`, `/ask-ground-mode`, `/ask/stream`, `/chat`, `/chat-ground-mode`, `/research`)
  - CHECK: `python -m pytest tests/unit/test_deprecation_headers.py -v`
  - EXPECT: all passed (5 passed)
  - EVIDENCE: 5 passed in 6.59s (`test_ask_route_has_deprecation_headers`, `test_research_route_has_deprecation_headers`, `test_ask_stream_route_deprecation_in_openapi`, `test_chat_route_has_deprecation_headers`, `test_legacy_routes_tagged_deprecated_in_spec`).

- [x] G3: Runtime `DeprecationWarning` fires when instantiating `GroundModeOrchestrator` and `ResearchModeOrchestrator`
  - CHECK: `python -m pytest tests/unit/test_orchestrator_deprecation.py -v`
  - EXPECT: all passed (6 passed)
  - EVIDENCE: 6 passed in 8.97s (`test_warns_on_instantiation` [Ground], `test_maintains_execute_method_signature` [Ground], `test_warns_on_instantiation` [Research], `test_maintains_run_method_signature` [Research], `test_both_orchestrators_importable`, `test_ground_factory_emits_deprecation_warning_for_legacy_path`).

- [x] G4: `docs/chapter4-api-contract.md` created — exhaustive endpoints list
  - CHECK: `Test-Path d:\koding\codes\NeosisLM\docs\chapter4-api-contract.md`
  - EXPECT: `True`
  - EVIDENCE: `True`. Document covers Workspaces, Conversations, Turns, Promotions, Scratchpad, Research Queue, Deprecated routes, Error envelopes, and HTTP status codes.

- [x] G5: `docs/chapter4-state-model.md` created — ERD + lifecycle state machines
  - CHECK: `Test-Path d:\koding\codes\NeosisLM\docs\chapter4-state-model.md`
  - EXPECT: `True`
  - EVIDENCE: `True`. Document contains full Mermaid ERD and state diagrams for Conversation, Turn, ResearchRun, Candidate/Artifact, Scratchpad, and Workspace Commit/Rollback model.

- [x] G6: `docs/chapter4-event-catalog.md` created — complete SSE event catalog
  - CHECK: `Test-Path d:\koding\codes\NeosisLM\docs\chapter4-event-catalog.md`
  - EXPECT: `True`
  - EVIDENCE: `True`. Document specifies all 16 event types (tokens, citations, ODR milestones, candidates, terminals), keep-alive ping format, and Last-Event-ID reconnect semantics.

- [x] G7: `docs/chapter4-ui-handoff.md` created — TypeScript types, state machines, sequence diagrams
  - CHECK: `Test-Path d:\koding\codes\NeosisLM\docs\chapter4-ui-handoff.md`
  - EXPECT: `True`
  - EVIDENCE: `True`. Document includes complete TypeScript type definitions, UI finite state machine, 6 Mermaid sequence diagrams (Ground, Research, Reconnection, Promotion Review, Commits/Rollback, Knowledge Graph), and implementation recipes.

- [x] G8: Zero frontend implementation code added (no .tsx/.ts/.jsx source files, no React/Vue components)
  - CHECK: `git status --short | Select-String "\.tsx|\.jsx|\.vue|src/components"`
  - EXPECT: (empty — no matches)
  - EVIDENCE: Command returned empty output with exit code 0. Only backend documentation, schemas, and tests modified.

- [x] G9: Full unit test suite passes (no new regressions)
  - CHECK: `python -m pytest tests/unit/ -q --tb=line`
  - EXPECT: 176 passed, 0 failed
  - EVIDENCE: 176 passed, 40 warnings in 39.27s across the entire `tests/unit/` suite. Zero failures.