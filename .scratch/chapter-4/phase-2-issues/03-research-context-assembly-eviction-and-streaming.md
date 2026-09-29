# 03: Research Context Assembly, Token Eviction & Live Working State Streaming

**What to build:**
A deterministic, audited Research context assembly engine that gathers recent conversation history, working memory, active scratchpad entries (conversation and workspace-pinned), accepted knowledge, and research evidence under a strict token budget. Lower-priority items are evicted in reverse priority, and an immutable context version manifest is persisted at turn submission. Furthermore, during research execution, structured observations and hypotheses are persisted to PostgreSQL and streamed via Redis Pub/Sub and SSE in real time.

**Blocked by:** 01: Baseline Seam Closure & Context Policy Boundary (Ground Isolation), 02: Durable Scratchpad State & Production Checkpointer Contract

**Status:** closed-done

- [x] `build_research_context()` implemented in `app/services/chat/context.py` aggregating current message, working memory, active scratchpad entries, recent conversation turns, accepted knowledge, research evidence, and output graph
- [x] Deterministic reverse-priority eviction under token budget: Output KG → older evidence → distant turns → older scratchpad → accepted knowledge (preserving current message + working memory)
- [x] Synchronous context snapshotting: `context_version` audit bundle (budget, total tokens, included items, evicted items with reasons) is persisted to `ConversationTurn.context_version` during `ChatService.submit_turn(mode="research")`
- [x] `run_research_agent_job` in `app/workers/tasks.py` persists structured scratchpad updates directly to PostgreSQL
- [x] Real-time event publishing: `run_research_agent_job` publishes `chat_events` over Redis Pub/Sub (`event_type="scratchpad_entry"`) during execution
- [x] Strict content policy: raw model chain-of-thought or unrestricted intermediate model outputs are never persisted to scratchpad or emitted as scratchpad events
- [x] `app/services/memory_router.py` refactored to cleanly separate write routing, context assembly, and policy filtering
- [x] Integration tests in `tests/unit/chat/test_research_context.py` and `tests/unit/chat/test_research_worker_streaming.py` pass cleanly
