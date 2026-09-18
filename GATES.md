# Gates for Phase 5: Ticket 3

- [x] Add LangChain tracing configuration to `GroundModeOrchestrator` execution (EVIDENCE: `app/orchestration/ground_mode.py:167` `with tracing_v2_enabled(project_name="NeosisLM-GroundMode"):`)
- [x] Add LangChain tracing configuration to `ResearchModeOrchestrator` execution (EVIDENCE: `app/orchestration/research_mode.py:183` `with tracing_v2_enabled(project_name="NeosisLM-ResearchMode"):`)
- [x] Ensure background tasks (`app/workers/tasks.py`) explicitly disable tracing (EVIDENCE: `app/workers/tasks.py:21` `os.environ["LANGCHAIN_TRACING_V2"] = "false"` overriding global trace, and `astream` wrapped in `tracing_v2_enabled`)
- [x] Run `pytest` or `py_compile` to ensure no syntax errors (EVIDENCE: `py_compile` on tasks.py, ground_mode.py, research_mode.py passed with code 0)

# Gates for Phase 6: Ticket 1

- [x] `pandas` and `pyarrow` added to project dependencies (EVIDENCE: `requirements.txt` contains `pandas` and `pyarrow`)
- [x] `WorkspaceExportService` created in `app/services/export.py` with `export_to_zip` method (EVIDENCE: `app/services/export.py:16` `async def export_to_zip(self, workspace_id: UUID) -> str:`)
- [x] Unit tests verify the archive creation and payload structure by mocking database and object store interactions (EVIDENCE: `pytest tests/test_export.py` passed 1 passed in 2.57s)
