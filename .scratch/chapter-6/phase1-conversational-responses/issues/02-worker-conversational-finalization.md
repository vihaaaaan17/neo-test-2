# 02: Worker persists conversational answers, no auto reports

**Status:** done (2026-10-09)

**Blocked by:** 01

- [x] Worker stores `text` as `assistant_message`; completion events carry `evidence` + `routing`.
- [x] No `ResearchReport` / `memory_candidate` / `promotion.available` for ordinary turns; `finalize_report` removed.
- [x] Worker tests updated: exactly one terminal event, no report rows.
