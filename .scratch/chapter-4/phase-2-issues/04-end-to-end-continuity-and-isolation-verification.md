# 04: End-to-End Ground ↔ Research Continuity & Full Verification

**What to build:**
Complete integration verification proving that Ground and Research operate seamlessly within the same conversation without violating the Ground evidence boundary. Distinctive research facts must never leak into Ground execution context, while conversation continuity is preserved across multi-turn mode switches. All existing test suites must pass without regression, and the codebase knowledge graph must be fully updated.

**Blocked by:** 03: Research Context Assembly, Token Eviction & Live Working State Streaming

**Status:** closed-done

- [x] Critical Ground Isolation Test (`tests/integration/chat/test_ground_isolation.py` & `tests/unit/chat/test_ground_isolation.py`): injects distinctive research knowledge and output graph facts and asserts with 100% precision that neither fact appears in Ground context or engine payload
- [x] Critical Ground Persistence Test: confirms executing Ground turns never creates `KnowledgeMemory` and never enqueues `sync_knowledge_to_graph_job`
- [x] Multi-turn Continuity Test (`tests/unit/chat/test_continuity.py`): executes Ground → Research → Ground sequence, verifying conversation history continuity while proving Ground context remains isolated
- [x] Research Context Budget Test: asserts items exceeding token budget trigger correct deterministic eviction order and persist `context_version` metadata
- [x] Full repository test suite passes with zero regressions (57/57 unit tests passed)
- [x] `graphify update .` executed and verified, updating `graphify-out/` artifacts cleanly
- [x] Final quality gates ledger documented in `.scratch/chapter-4/GATES_PHASE_2.md`
