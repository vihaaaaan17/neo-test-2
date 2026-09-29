# Gates Ledger: Phase 2 Ticket 03 — Research Context Assembly, Eviction & Live Working State Streaming

- [x] GATE 1: `build_research_context()` implemented in `app/services/chat/context.py`
  - CHECK: inspect `app/services/chat/context.py` for `build_research_context`
  - EXPECT: aggregates current message, working memory, active scratchpad entries (conversation + pinned), recent turns, accepted knowledge, research evidence, output graph
  - EVIDENCE: Verified in `app/services/chat/context.py`. Assembles all 7 components into `ResearchContext` with `ContextItemManifest`. Tested in `tests/unit/chat/test_research_context.py::test_build_research_context_aggregates_all_components`.

- [x] GATE 2: Deterministic reverse-priority eviction under token budget
  - CHECK: inspect eviction algorithm in `app/services/chat/context.py`
  - EXPECT: drops in strict order: Output KG -> older evidence -> distant turns -> older scratchpad -> accepted knowledge; preserves current message and working memory
  - EVIDENCE: Verified in `app/services/chat/context.py`. Eviction pool sorts eligible candidates (priority ranks 1 to 5) while strictly preserving ranks 6 (working memory) and 7 (current query). Tested and verified in `tests/unit/chat/test_research_context.py::test_reverse_priority_eviction_order` and `test_working_memory_and_message_preserved_even_when_budget_exceeded`.

- [x] GATE 3: Synchronous context snapshotting in `ChatService.submit_turn(mode="research")`
  - CHECK: inspect `app/services/chat/service.py` `submit_turn`
  - EXPECT: `ConversationTurn.context_version` stores snapshot manifest (budget, estimated_tokens, included_items, evicted_items, eviction_reasons) at submission time before enqueuing ARQ job
  - EVIDENCE: Verified in `app/services/chat/service.py` in both `submit_turn` and `stream_turn`. Persists `context_version={"research_context": research_ctx.context_version.model_dump(mode="json")}` to `ConversationTurn`. Tested and verified in `tests/unit/chat/test_research_worker_streaming.py::test_submit_research_turn_snapshots_context_version`.

- [x] GATE 4: Structured scratchpad persistence in `run_research_agent_job`
  - CHECK: inspect `app/workers/tasks.py`
  - EXPECT: structured observations, hypotheses, and findings are persisted to `ScratchpadRepository` during research run execution
  - EVIDENCE: Verified in `app/workers/tasks.py`. During `engine.astream_events`, structured `scratchpad_entry` events create active entries via `ScratchpadRepository.create_entry()`. Tested and verified in `tests/unit/chat/test_research_worker_streaming.py::test_worker_persists_structured_scratchpad_and_publishes_event`.

- [x] GATE 5: Real-time `scratchpad_entry` event publishing
  - CHECK: inspect event emissions in `app/workers/tasks.py`
  - EXPECT: publishes `event_type="scratchpad_entry"` via Redis Pub/Sub on channel `turn_events:{turn_id}`
  - EVIDENCE: Verified in `app/workers/tasks.py` and `app/services/chat/service.py`. Worker publishes `event_type="scratchpad_entry"` to `research_events:{run_id}` and `turn_events:{turn_id}`, and `_bridge_research_events_background` bridges it to turn SSE streams and `chat_events`. Tested and verified in `tests/unit/chat/test_research_worker_streaming.py::test_worker_persists_structured_scratchpad_and_publishes_event`.

- [x] GATE 6: Strict content filtering (no raw model CoT in scratchpad)
  - CHECK: inspect schema / helper validating structured scratchpad updates in worker
  - EXPECT: raw CoT or unstructured reasoning text is rejected / sanitized; only structured entries with valid `entry_type` and clean summary content are stored
  - EVIDENCE: Verified in `sanitize_scratchpad_content()` in `app/services/chat/context.py` and enforced in `app/workers/tasks.py`. Tested and verified in `tests/unit/chat/test_research_context.py::test_sanitize_scratchpad_content` and `tests/unit/chat/test_research_worker_streaming.py::test_worker_rejects_raw_chain_of_thought_scratchpad`.

- [x] GATE 7: `app/services/memory_router.py` refactoring
  - CHECK: inspect `app/services/memory_router.py`
  - EXPECT: memory router leverages `GroundContextPolicy` and `ResearchContextPolicy` and routes context operations through policy-governed assembly
  - EVIDENCE: Verified in `app/services/memory_router.py`. Prohibits Ground mode from writing `KnowledgeMemory` per `GroundContextPolicy`, and routes context assembly through `assemble_ground_context` and `assemble_research_context`. Tested in `tests/unit/chat/test_research_context.py::test_memory_router_policy_enforcement` and `tests/test_memory_router.py`.

- [x] GATE 8: Unit tests passing 100%
  - CHECK: `python -m pytest tests/unit/chat/test_research_context.py tests/unit/chat/test_research_worker_streaming.py -v`
  - EXPECT: all unit tests pass with zero failures
  - EVIDENCE: 9/9 tests passed in 10.98s. Full 34-test Phase 2 suite passed in 9.73s.
