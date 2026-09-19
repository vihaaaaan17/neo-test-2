# 03: Phase 2 Lifecycle & Event Service

**What to build:** 
A service (`app/services/research/lifecycle.py`) that acts as the sole authority for state transitions of `ResearchRun` and `ResearchTask`. It ensures invalid transitions are rejected and automatically records `ResearchEvent` rows for auditability when states successfully change.

**Blocked by:** 02 (02-unified-research-repository.md)

**Status:** ready-for-agent

- [x] Create `app/services/research/lifecycle.py`.
- [x] Implement strict state machine validation for `ResearchRun` (CREATED -> PLANNING -> RESEARCHING -> SYNTHESIZING -> FINALIZING -> COMPLETED/PARTIAL/FAILED/CANCELLED).
- [x] Implement strict state machine validation for `ResearchTask` (PENDING -> RUNNING -> COMPLETED/PARTIAL/FAILED/CANCELLED/SKIPPED).
- [x] Integrate with the research repository to persist transitions and automatically emit/save corresponding `ResearchEvent` records.
- [x] Write unit tests verifying that invalid state transitions raise clear exceptions.
