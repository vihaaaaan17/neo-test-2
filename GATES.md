# Gates for Phase 5: Ticket 3

- [x] Add LangChain tracing configuration to `GroundModeOrchestrator` execution (EVIDENCE: `app/orchestration/ground_mode.py:167` `with tracing_v2_enabled(project_name="NeosisLM-GroundMode"):`)
- [x] Add LangChain tracing configuration to `ResearchModeOrchestrator` execution (EVIDENCE: `app/orchestration/research_mode.py:183` `with tracing_v2_enabled(project_name="NeosisLM-ResearchMode"):`)
- [x] Ensure background tasks (`app/workers/tasks.py`) explicitly disable tracing (EVIDENCE: `app/workers/tasks.py:21` `os.environ["LANGCHAIN_TRACING_V2"] = "false"` overriding global trace, and `astream` wrapped in `tracing_v2_enabled`)
- [x] Run `pytest` or `py_compile` to ensure no syntax errors (EVIDENCE: `py_compile` on tasks.py, ground_mode.py, research_mode.py passed with code 0)
