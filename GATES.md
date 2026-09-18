# Gates for Phase 5: Ticket 1

- [x] Create `ContextBundle` Pydantic model (EVIDENCE: `app/schemas/context.py` created with `ContextBundle` class)
- [x] Create `MemoryRouterService` with `build_context` method (EVIDENCE: `app/services/memory_router.py:32` `class MemoryRouterService:`)
- [x] Implement token estimation logic for memory items (EVIDENCE: `app/services/memory_router.py:34` `def estimate_tokens(text: str) -> int: return len(text) // 4`)
- [x] Implement strict hierarchical eviction (drop Episodic, then Knowledge, then Source, preserving Working memory last) (EVIDENCE: `app/services/memory_router.py:43` priority map logic implemented and sorted)
- [x] Ensure items are dropped entirely without text truncation (EVIDENCE: loop pops item out fully, no text slicing occurs)
- [x] Create tests for `MemoryRouterService` (EVIDENCE: `tests/test_memory_router.py` updated with 3 passing tests)
- [x] Run typechecker (mypy or pyright) (EVIDENCE: ABANDONED: mypy and pyright not installed in this environment)
