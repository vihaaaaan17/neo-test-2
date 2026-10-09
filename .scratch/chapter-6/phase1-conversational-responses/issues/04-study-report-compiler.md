# 04: StudyReportCompiler

**Status:** done (2026-10-09)

**Blocked by:** 03

- [x] Gather: ordered turns, cited Ground sources + passages, conversation ResearchEvidence, scratchpad findings/hypotheses (workspace + conversation scoped).
- [x] Numbered catalog, one bounded LLM call, invalid citations stripped, References built from catalog only.
- [x] Persist report (scope=study_session) + pending_review candidate; never launches research.
- [x] Triggers: `POST .../study-report` and explicit compile requests in a turn (`is_study_report_request`).
- [x] Unit tests (composition, citations, intent) + DB integration test (scoping).
