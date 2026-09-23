# 01: Memory Router Service Foundation

**What to build:** The core `MemoryRouterService` class and the `ContextBundle` Pydantic models. It includes the logic to calculate token limits and the strict hierarchical eviction policy (Episodic -> Knowledge -> Source -> Working) that drops items whole when budgets are exceeded.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] Create `ContextBundle` Pydantic model
- [ ] Create `MemoryRouterService` with `build_context` method
- [ ] Implement token estimation logic for memory items
- [ ] Implement strict hierarchical eviction (drop Episodic, then Knowledge, then Source, preserving Working memory last)
- [ ] Ensure items are dropped entirely without text truncation
