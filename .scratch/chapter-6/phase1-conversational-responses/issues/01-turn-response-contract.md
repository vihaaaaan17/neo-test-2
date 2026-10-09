# 01: turn_response engine contract

**Status:** done (2026-10-09)

- [x] `turn_response()` / `TURN_RESPONSE` in `engine.py`; `final_report` removed from all adapters.
- [x] ODR: response-style instruction via the user message; GPT-R: `write_report(custom_prompt=...)`; STORM: `format="article"`.
- [x] Contract tests: all three adapters yield exactly one `turn_response`.
