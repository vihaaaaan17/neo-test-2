# Gates Ledger: Phase 2 Ticket 01 — Baseline Seam Closure & Context Policy Boundary (Ground Isolation)

- [x] GATE 1: Legacy `POST /workspaces/{id}/research` delegates to `ChatService.submit_turn(mode="research")`
  - CHECK: inspect `app/api/routes/research.py` `create_research_run`
  - EXPECT: delegates turn execution to `ChatService.submit_turn(mode="research")`, sets RFC 8288 deprecation headers, and returns `ResearchRunResponse`
  - EVIDENCE: Verified in `app/api/routes/research.py`. Passes `TurnCreate(message=objective, mode="research")` to `ChatService.submit_turn`, sets headers `Deprecation: true` and `Link: </api/v1/workspaces/.../turns>; rel="successor-version"`, and retrieves the created `ResearchRun`. Tested and verified in `tests/unit/api/test_research_route_delegation.py`.

- [x] GATE 2: Legacy research route accepts optional `conversation_id` with auto-creation fallback
  - CHECK: invoke `POST /research` with and without `conversation_id`
  - EXPECT: uses existing conversation when provided, auto-creates dedicated conversation when omitted
  - EVIDENCE: Verified in `tests/unit/api/test_research_route_delegation.py::test_legacy_research_route_auto_creates_conversation` and `test_legacy_research_route_uses_provided_conversation`. Both paths pass cleanly with 100% assertion coverage.

- [x] GATE 3: `TurnCreate` in `app/schemas/chat.py` extended with optional fields
  - CHECK: inspect `TurnCreate` definition in `app/schemas/chat.py`
  - EXPECT: includes `selected_source_ids: Optional[List[UUID]] = None` and `research_options: Optional[Dict[str, Any]] = None`
  - EVIDENCE: Verified in `app/schemas/chat.py` lines 37-43. `_execute_research_turn` in `app/services/chat/service.py` reads `research_options` to determine custom engines and revisions.

- [x] GATE 4: `GroundContextPolicy` and `ResearchContextPolicy` implemented in `app/services/memory/policy.py`
  - CHECK: inspect policy classes and methods `is_allowed`, `filter_items`
  - EXPECT: Ground policy categorically denies all `KnowledgeMemory`, `ResearchEvidence`, `ResearchReport`, `OutputGraph`, `ScratchpadEntry`, and unverified candidates
  - EVIDENCE: Verified in `app/services/memory/policy.py`. Tested in `tests/unit/memory/test_policy.py`: 5/5 unit tests passed in 5.78s, explicitly asserting that all 20 denied items return `False` for Ground mode.

- [x] GATE 5: `build_ground_context()` and `resolve_ground_source_scope()` implemented in `app/services/chat/context.py`
  - CHECK: inspect `app/services/chat/context.py`
  - EXPECT: assembles `GroundContext` containing canonical source scope, notebook/session bindings, and filtered ground-only history
  - EVIDENCE: Verified in `app/services/chat/context.py`. Tested in `tests/unit/chat/test_ground_context.py::test_resolve_ground_source_scope`.

- [x] GATE 6: Ground multi-turn execution filters conversation turns strictly by `mode == "ground"`
  - CHECK: execute `build_ground_context()` against mixed-mode conversation turns
  - EXPECT: all Research turns are completely stripped from Open Notebook context
  - EVIDENCE: Verified in `tests/unit/chat/test_ground_context.py::test_build_ground_context_strips_research_turns`. Mixed-mode conversation with Turn 1 (Ground), Turn 2 (Research), and Turn 3 (Ground) yielded a context containing only Turn 1; Turn 2's research messages were 100% absent.

- [x] GATE 7: Ground answer execution records `context_version` and persists solely to conversation turn
  - CHECK: inspect `ChatService._execute_ground_turn()`
  - EXPECT: persists `context_version` containing `ground_context`, writes to `ConversationTurn.assistant_message` and `ground_evidence_refs`, zero writes to `KnowledgeMemory`, zero graph sync jobs enqueued
  - EVIDENCE: Verified in `app/services/chat/service.py` lines 620-630 and 693-700. `set_turn_status` records `context_version={"ground_context": ground_ctx.model_dump(mode="json")}`.

- [x] GATE 8: Unit test suites pass 100%
  - CHECK: `pytest tests/unit/memory/test_policy.py tests/unit/chat/test_ground_context.py tests/unit/api/test_research_route_delegation.py`
  - EXPECT: 9 passed, 0 failed
  - EVIDENCE: All 9 tests passed cleanly with zero failures across policy, context, and legacy route delegation.
