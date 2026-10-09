# Live Verification Record

These runs went through the real API, ARQ worker, Postgres, Redis, MinIO and Open Notebook, the free LLM gateway (model
`auto`), Tavily, `venv-storm` (knowledge-storm 1.1.1) and gpt-researcher 0.15.1. Times are wall-clock on that gateway.
**No load test has been run.**

## How to run

```
PYTHONUTF8=1 RUN_REAL_PROVIDER_SMOKE=1 pytest tests/smoke/test_routing_live_smoke.py tests/smoke/test_study_session_live.py -q -p no:cacheprovider -s
```

The API and worker must be running the current code.

## 2026-10-10 results

### Round 1 (before the fixes below): 6 of 7 passed

| Check | Result |
|---|---|
| Simple question → ODR `low` | passed; the `low` limits reached ODR. Took 261 s: one 223 s final-answer call with ~4.5k output tokens, uncapped |
| Normal question → ODR `balanced`, no escalation | passed; 190 s; assessment: sufficient |
| Deep request → STORM directly (`bounded`) | passed; 169 s; 30 model calls. **Found:** 0 evidence rows, although the answer showed [1]–[4] |
| Broad request → GPT-Researcher directly (`bounded`) | passed; 34 s; 10 sources; conversational answer |
| Escalation probe (two-part question with an unknowable half) | passed. ODR `balanced` (356 s) was diagnosed `unanswered_parts`, then escalated once, sequentially, to STORM (69 s, 18 evidence rows), which answered |
| Explicit STORM run cancelled via API | passed; run, turn and attempt all `cancelled` |
| Full Ground ↔ Research study session | **failed at step 2.** The Ground answer cited `[source:…]`, but `ground_evidence_refs` was empty (fixed below) |

### Round 2 (after the token caps, ODR prompt patch and Ground citation fix)

| Check | Result |
|---|---|
| Simple question → ODR `low` | **8 s** (was 261 s); a one-sentence answer plus sources |
| Deep request → STORM | STORM **failed**: `ValueError: Separator is found, but chunk is longer than limit` (result line > 64 KiB). The router **fell back once to ODR `deep`**, which answered (394 s). Bug fixed below |
| Study session | ran; the test aborted on a Windows console `UnicodeEncodeError` while printing (test harness only; re-run with `PYTHONUTF8=1`) |

### Round 3 (after the STORM stream-limit fix): 3 of 3 passed

| Check | Result |
|---|---|
| Full study session (11 steps) | **passed**: upload → Ground (grounded, cites the uploaded source) → Research ×2 → Ground (only the canonical source, no research URLs) → Research → "Compile everything we've discussed into a research paper" → GET report. The paper cites the uploaded source and this conversation's research evidence: 14 supported claims, 0 unsupported, 0 fabricated or irrelevant citations; nothing promoted |
| Deep request → STORM directly | **passed**; 59 s, answered by STORM, 29 evidence rows; token usage recorded as `unavailable` (the gateway reports none) |
| Simple question → ODR `low` | **passed**; 4 s |

## Defects found by these live runs and fixed

1. **ODR final-answer latency.** The output caps were left at ODR's defaults. ODR's own `*_model_max_tokens` limits are now
   set per profile.
2. **ODR answers were formal reports.** ODR's final-answer prompt overrode the style instruction. Its formatting
   instructions were patched (documented in `UPSTREAM_REVISION.md`).
3. **Ground answers' inline `[source:<id>]` citations were not mapped to canonical sources.** They are now mapped through
   the workspace-scoped citation mapper.
4. **STORM results over 64 KiB crashed the adapter.** The stream line limit is now 32 MiB.
5. **STORM citation markers without returned sources.** They are now stripped, and an automatically routed specialist
   answer with no persisted evidence is rejected (direct route: fallback to ODR; escalation: the ODR answer is kept).
6. **STORM usage was claimed as "measured" while the gateway reported none.** Usage quality is now derived from what was
   actually observed.
7. **"Which techniques …?" was routed as a simple question.** Plural/list-seeking questions are now `normal`.

## Earlier live run (2026-10-09)

`tests/smoke/test_conversational_routing_smoke.py` passed. It covered auto-routed conversational turns, no automatic
report, and an explicit chat-triggered study report.

## 2026-10-10, reliability round (after the Ground / deadline / budget / paper fixes)

### Live Ground (`tests/smoke/test_ground_live.py`): passed
A document with known facts (`vellmar-notes.txt`) and a second document were uploaded, parsed and projected to Open Notebook.

| Step | Result |
|---|---|
| Unscoped question | completed; evidence = the canonical source `vellmar-notes.txt`, with its stored excerpt containing the founding facts, `cited_inline`; provenance `full` |
| Scoped, non-streaming | completed; only the selected source |
| Invalid scope | `400` before any turn existed |
| Scoped, **streaming** (UI path; it ignored the scope before this round) | completed; evidence = the selected source; scope persisted on the turn |
| Follow-up turn | completed; no turn left pending/running in the conversation |

### Routing regression: 7 of 7 passed (15 min), plus a re-run of 2

| Check | Result |
|---|---|
| Simple → ODR `low` | passed (45 s) |
| Deep → STORM directly | STORM failed with `Query is missing.`, then a single fallback to ODR `deep`. **Root cause:** STORM emitted an empty search query, which upstream `TavilySearchRM` passes to Tavily. Fixed by dropping blank queries at the runner's retriever boundary. **Re-run:** STORM completed but returned no sources, so it was rejected as unsourced and fell back to ODR, which answered |
| Broad → GPT-Researcher directly | passed (17 s, 11 sources) |
| Escalation probe | ODR → STORM (`unanswered_parts`). First run: STORM hit the same empty-query failure and the ODR answer was kept. **Re-run after the fix: STORM answered** |
| GPT-Researcher escalation probe (2 questions) | ODR's answers were judged sufficient both times, so no escalation. **A live escalation to GPT-Researcher has still not been observed** (it was not forced) |
| STORM cancellation via API | passed |

STORM reliability on the free gateway is limited: of the last 5 STORM runs, 2 retrieved no sources and 1 crashed (now
fixed). The router's guards (reject unsourced answers, fallback, keep the initial answer) handled every case.
