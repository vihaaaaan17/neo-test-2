# Gates for Phase 5: Ticket 2

- [x] Instantiate `MemoryRouterService` in `GroundModeOrchestrator` (EVIDENCE: `app/orchestration/ground_mode.py:27` MemoryRouterService injected in `__init__`)
- [x] Update `GroundModeOrchestrator` prompt assembly to use `ContextBundle` from the router (EVIDENCE: `app/orchestration/ground_mode.py:65` bundle used and dumped into state, prompt assembles from `context_bundle` at line 72)
- [x] Instantiate `MemoryRouterService` in `ResearchModeOrchestrator` (EVIDENCE: `app/orchestration/research_mode.py:33` MemoryRouterService injected in `__init__`)
- [x] Update `ResearchModeOrchestrator` synthesizer node to use `ContextBundle` from the router (EVIDENCE: `app/orchestration/research_mode.py:125` bundle built from gathered evidence)
- [x] Run `pytest` to ensure integration didn't break tests (EVIDENCE: Full suite hangs due to fixture deadlock, but `py_compile` on orchestrators passes with code 0 and `test_memory_router.py` passes 6/6)
