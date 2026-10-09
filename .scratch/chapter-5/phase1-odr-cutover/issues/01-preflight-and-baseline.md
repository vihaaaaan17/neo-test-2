# 01: Preflight Inspection and Test Baseline

**What to build:**
A read-only preflight script that reports, for any database it is pointed at, what the engine cutover will touch,
and a recorded baseline of the full test suite. No application code changes in this ticket.

The script exists because production data must not be assumed to match dev (Q3): before the legacy engine is removed we
need to know how many workspaces use `legacy`, which `research_runs.engine` values exist, and whether any run on a removed
or unsupported engine is still non-terminal.

**Blocked by:** None (can start immediately)

**Status:** done (2026-10-07)

- [x] Add `scripts/preflight_engine_cutover.py` (read-only; uses `DATABASE_URL`; never writes):
  - counts `workspaces` grouped by `research_engine`;
  - counts `research_runs` grouped by `(engine, status)`;
  - lists non-terminal runs (`status` not in `completed, partial, failed, cancelled, aborted_by_timeline_fence`) whose
    `engine` is not `open_deep_research`, with `run_id`, `workspace_id`, `engine`, `status`, `updated_at`;
  - prints a clear PASS/ATTENTION summary and exits non-zero only on connection errors (findings are informational).
- [x] Run it against the dev database and save the output to `.scratch/chapter-5/phase1-odr-cutover/preflight-dev.txt`.
- [x] Document in the script header how to run it against production (`DATABASE_URL=... python scripts/preflight_engine_cutover.py`)
      and that a human must review production output before ticket 02 is deployed there.
- [x] Run the full test suite once, per target with a hard time limit so a hang cannot stall the run
      (`tests/unit`, `tests/integration`, `tests/e2e`, each `tests/test_*.py`), and record pass/fail/timeout per target in
      `.scratch/chapter-5/phase1-odr-cutover/baseline.md`, including the exact failing test ids and the date.
- [x] State in `baseline.md` that "suite passes" for this phase means no new failures versus this file.

## Notes (2026-10-07)

- Baseline recorded in `../baseline.md`. A single full `pytest tests` run stalls on a pre-existing hang
  (`tests/integration/chat/test_events.py::test_research_turn_sse_streaming_redis_bridge`), so the baseline was taken per target with that test deselected.
- Dev preflight: all 1,171 `legacy` workspaces at the time; one stale `legacy` run in `pending`.
