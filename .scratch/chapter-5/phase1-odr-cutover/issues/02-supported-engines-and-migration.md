# 02: SUPPORTED_ENGINES, Admission Validation, and ODR Default Migration

**What to build:**
Make ODR the database/model default and reject unsupported engine names at the admission choke point, so a bad engine
name fails before a `ResearchRun` exists instead of inside the worker.

**Blocked by:** 01

**Status:** done (2026-10-07)

- [x] Add `SUPPORTED_ENGINES = ("open_deep_research",)` to `app/integrations/research_engine/engine.py` (no heavy imports there).
- [x] In `ResearchAdmissionController.admit_research_run` (`app/services/research/admission.py`) validate `engine` against
      `SUPPORTED_ENGINES` before any DB write and raise `HTTPException(422, detail="unsupported_research_engine")`.
      `storm` and `gpt_researcher` are rejected the same way.
- [x] `app/models/workspace.py`: change `Workspace.research_engine` default from `"legacy"` to `"open_deep_research"`.
- [x] New alembic migration chained from the current head `f7a8b9c0d1e2` (do not edit `5172a2f9d3aa`):
  - `UPDATE workspaces SET research_engine='open_deep_research' WHERE research_engine='legacy'`;
  - change the server default to `'open_deep_research'`;
  - `downgrade()` restores only the server default to `'legacy'`; add a comment that the data update is not reversible;
  - no check constraint, no changes to `research_runs`.
- [x] Verify `create_workspace` in `app/api/routes/workspaces.py` no longer yields legacy-backed workspaces.
- [x] Update any existing test that calls `admit_research_run` (or posts a research turn) with an unsupported engine string
      such as `legacy`, `test_engine` or `odr`, so the suite stays green; do not touch tests that only use the string as an
      ORM fixture value (ticket 04).
- [x] Add unit tests: supported engine admitted; unsupported/legacy/storm/gpt_researcher rejected with 422 and no run created.
- [x] Run `scripts/validate_migrations.py` and `tests/unit/test_migrations.py`; both must pass.
- [x] Re-run the preflight script against the migrated dev DB and confirm no `legacy` workspaces remain.

## Notes (2026-10-07)

- Migration: `alembic/versions/4fbc1a48c26c_default_research_engine_to_open_deep_research.py` (revision ID generated after the first choice collided with an
  existing migration; caught by the DAG audit). Dev DB upgraded, downgraded and upgraded again via the alembic CLI; all workspaces are now `open_deep_research`.
- `scripts/validate_migrations.py` static audits pass (19 revisions, single head). Its optional live round-trip step is broken independently of this ticket
  (un-awaited `run_async_migrations` coroutine); not fixed here.
- Pinned-head assertions updated: `tests/unit/test_migrations.py` (19 revisions, new head) and `tests/unit/research/test_timeline_promotion_graph.py`
  (now inspects the `f7a8b9c0d1e2` migration instead of "the head").
- Extra fix found while verifying: the turn row is created before admission, so an admission rejection (422 here, and 429 quotas before) left the turn `pending`
  and blocked the conversation with 409. `ChatService._admit_research_run_or_close_turn` now closes the turn as `failed` before re-raising
  (both `stream_turn` and `_execute_research_turn`). Test: `tests/unit/chat/test_research_admission_rejection.py`.
- Test fixes required by the stricter admission: `tests/integration/chat/test_turns.py` and `test_events.py` workspace fixtures now use `open_deep_research`;
  `MockArqRedis` in `test_turns.py` gained the sorted-set methods the ODR rate-limit check calls (legacy previously bypassed it).
- Regression check vs baseline: same targets, 287 passed in the first group and the same 5 pre-existing failures in the second; no new failures.
