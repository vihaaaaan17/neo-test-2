# Quality Gates Ledger: Chapter 4 Phase 2 — Memory, Working State & Context Isolation

## Overview
This master ledger records the verified engineering evidence for Chapter 4 Phase 2 across all 4 tickets:
- Ticket 01: Baseline Seam Closure & Context Policy Boundary (Ground Isolation)
- Ticket 02: Durable Scratchpad State & Production Checkpointer Contract
- Ticket 03: Research Context Assembly, Token Eviction & Live Working State Streaming
- Ticket 04: End-to-End Ground <-> Research Continuity & Full Verification

---

### Ticket 01: Baseline Seam Closure & Context Policy Boundary (Ground Isolation)
- [x] GATE 1: Legacy Research Route delegation with auto-conversation creation & RFC 8288 deprecation headers
  - EVIDENCE: Verified in `app/api/routes/research.py`. 2/2 unit tests passed in `tests/unit/api/test_research_route_delegation.py`.
- [x] GATE 2: TurnCreate schema extension (`selected_source_ids`, `research_options`)
  - EVIDENCE: Verified in `app/schemas/chat.py`.
- [x] GATE 3: Context Policy Boundary (`GroundContextPolicy` & `ResearchContextPolicy`)
  - EVIDENCE: Verified in `app/services/memory/policy.py`. 5/5 unit tests passed in `tests/unit/memory/test_policy.py`.
- [x] GATE 4: Ground Context Assembly filtering (`build_ground_context`)
  - EVIDENCE: Verified in `app/services/chat/context.py`. Multi-turn history excludes research turns. 2/2 unit tests passed in `tests/unit/chat/test_ground_context.py`.
- [x] GATE 5: Zero KnowledgeMemory writes on Ground execution
  - EVIDENCE: Verified in `ChatService._execute_ground_turn`. Persists exclusively to `assistant_message`, `ground_evidence_refs`, and `chat_events`.

---

### Ticket 02: Durable Scratchpad State & Production Checkpointer Contract
- [x] GATE 1: SQLAlchemy model `ScratchpadEntry` created and indexed
  - EVIDENCE: Verified in `app/models/scratchpad.py` and exported in `app/models/__init__.py`. Composite indexes on `(workspace_id, lifecycle)`, `(conversation_id, lifecycle)`, `(workspace_id, is_pinned_to_workspace)`.
- [x] GATE 2: Alembic migration for `scratchpad_entries` table
  - EVIDENCE: Verified in `alembic/versions/e6f7a8b9c0d1_add_scratchpad_entries.py`.
- [x] GATE 3: `ScratchpadRepository` transactional CRUD, pinning, and lifecycle methods
  - EVIDENCE: Verified in `app/repositories/scratchpad.py`. Tested in `tests/unit/memory/test_scratchpad.py`.
- [x] GATE 4: Pydantic schemas in `app/schemas/scratchpad.py`
  - EVIDENCE: Verified in `app/schemas/scratchpad.py`. Tested in `tests/unit/memory/test_scratchpad.py`.
- [x] GATE 5: REST API endpoints in `app/api/routes/scratchpad.py`
  - EVIDENCE: Verified in `app/api/routes/scratchpad.py` and registered in `app/main.py`. Tested in `tests/unit/api/test_scratchpad_routes.py`.
- [x] GATE 6: Checkpointer contract with fail-fast production check
  - EVIDENCE: Verified in `app/services/working_memory.py`. 4/4 tests passed in `tests/unit/memory/test_checkpointer.py`.
- [x] GATE 7: Startup validation hooks registered
  - EVIDENCE: Verified in `app/main.py` lifespan and `app/workers/settings.py` on_startup.

---

### Ticket 03: Research Context Assembly, Eviction & Live Working State Streaming
- [x] GATE 1: `build_research_context()` aggregating all 7 context sources
  - EVIDENCE: Verified in `app/services/chat/context.py`. Tested in `tests/unit/chat/test_research_context.py`.
- [x] GATE 2: Deterministic reverse-priority eviction under token budget
  - EVIDENCE: Drops Output KG -> evidence -> distant turns -> older scratchpad -> accepted knowledge; preserves current query and working memory. Tested in `tests/unit/chat/test_research_context.py`.
- [x] GATE 3: Synchronous context snapshotting during research turn submission
  - EVIDENCE: Verified in `app/services/chat/service.py` (`submit_turn` & `stream_turn`). Tested in `tests/unit/chat/test_research_worker_streaming.py`.
- [x] GATE 4: Structured scratchpad persistence in `run_research_agent_job`
  - EVIDENCE: Verified in `app/workers/tasks.py`. Tested in `tests/unit/chat/test_research_worker_streaming.py`.
- [x] GATE 5: Real-time `scratchpad_entry` event publishing via Redis Pub/Sub
  - EVIDENCE: Verified in `app/workers/tasks.py` and `app/services/chat/service.py`. Tested in `tests/unit/chat/test_research_worker_streaming.py`.
- [x] GATE 6: Strict content filtering (no raw model CoT in scratchpad)
  - EVIDENCE: Verified via `sanitize_scratchpad_content()` in `app/services/chat/context.py`. Tested in `tests/unit/chat/test_research_context.py`.
- [x] GATE 7: `MemoryRouter` policy refactoring
  - EVIDENCE: Verified in `app/services/memory_router.py`. Prohibits Ground mode from writing `KnowledgeMemory`. Tested in `tests/unit/chat/test_research_context.py`.

---

### Ticket 04: End-to-End Ground <-> Research Continuity & Full Verification
- [x] GATE 1: Critical Ground Isolation Test (zero distinctive research fact leak into Ground context or engine payload)
  - CHECK: `tests/unit/chat/test_ground_isolation.py`
  - EXPECT: Assert 100% precision that DISTINCTIVE_RESEARCH_FACT and DISTINCTIVE_GRAPH_FACT never appear in Ground context
  - EVIDENCE: Verified in `tests/unit/chat/test_ground_isolation.py::test_critical_ground_isolation_zero_leak`. Injected `DISTINCTIVE_RESEARCH_FACT` and `DISTINCTIVE_GRAPH_FACT`; verified 100% absence from Ground context.
- [x] GATE 2: Critical Ground Persistence Test (zero KnowledgeMemory writes, zero sync_knowledge_to_graph_job enqueued)
  - CHECK: `tests/unit/chat/test_ground_isolation.py`
  - EXPECT: Ground turn completion creates 0 KnowledgeMemory rows and 0 graph sync tasks
  - EVIDENCE: Verified in `tests/unit/chat/test_ground_isolation.py::test_critical_ground_persistence_zero_knowledge_memory`. Ground turn completion verified to add zero KnowledgeMemory objects and zero graph sync tasks.
- [x] GATE 3: Multi-turn Continuity Test (Ground -> Research -> Ground sequence)
  - CHECK: `tests/unit/chat/test_continuity.py`
  - EXPECT: Conversational history is continuous, but Ground turn 3 only sees Ground turn 1 history, stripping Research turn 2
  - EVIDENCE: Verified in `tests/unit/chat/test_continuity.py::test_multi_turn_ground_research_ground_continuity`. Research turn 2 had full visibility of prior ground turn, while Ground turn 3 preserved Ground turn 1 history and strictly stripped Research turn 2 unverified hypotheses.
- [x] GATE 4: Full unit test suite regression pass
  - CHECK: `pytest tests/unit/ -v`
  - EXPECT: 100% passing across all suites
  - EVIDENCE: 57 of 57 unit tests passed in 36.68s with zero regressions.
- [x] GATE 5: Graphify knowledge graph updated
  - CHECK: `graphify update .`
  - EXPECT: Topology and reports updated cleanly
  - EVIDENCE: Rebuilt 1114 nodes, 2735 edges, 53 communities in `graphify-out/`.
