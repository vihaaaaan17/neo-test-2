# 03: Ground Engine Factory Abstraction & Cutover

**What to build:** Implements a clean, decoupled `get_ground_engine` FastAPI dependency router to abstract engine selection. Refactors the workspace routes to use it, dropping inline conditionals, and formally flips the default value of `OPEN_NOTEBOOK_ENABLED` to `True`.

**Blocked by:** 01 (Evaluation Matrix must be established first to validate the cutover)

**Status:** ready-for-agent

- [ ] Create `app/services/ground/factory.py`.
- [ ] Implement `get_ground_engine` dependency that conditionally returns `OpenNotebookGroundEngine` or `GroundModeOrchestrator` based on `settings.OPEN_NOTEBOOK_ENABLED`.
- [ ] Update `app/api/routes/workspaces.py` routes (`ask_ground_mode`, `ask_ground_mode_stream`) to accept `Depends(get_ground_engine)`.
- [ ] Update `app/core/config.py` to change `OPEN_NOTEBOOK_ENABLED = True` by default.
- [ ] Ensure existing integration tests run against the newly enabled engine successfully.
