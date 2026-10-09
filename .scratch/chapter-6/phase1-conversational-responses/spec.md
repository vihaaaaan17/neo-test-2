# Chapter 6, Phase 1: Conversational Turns and Explicit Study-Session Reports

## Objective

A Research turn answers like a study partner would. It returns a `ConversationalResponse + Evidence`, not a formal report.
A formal, cited paper is produced only when the user explicitly asks to compile the study session.

## Current state (inspected 2026-10-09)

- Every adapter yields `{"status": "final_report", "report": str}`. The worker calls `ResearchService.finalize_report`, which
  writes a `ResearchReport` plus a `pending_review` `memory_candidate` for every completed run. The turn's `assistant_message`
  is then read back from that report.
- `ResearchReport.run_id` and `ResearchArtifact.run_id` are `NOT NULL`, and candidate review scopes by joining to `research_runs`.
- Ground turns already return Open Notebook's answer as `assistant_message`, with source ids in `ground_evidence_refs`.

## Decisions

1. **Turn response contract.** The engine contract becomes progress events plus exactly one
   `{"status": "turn_response", "text": str, "format": "conversational" | "article", "evidence_refs": [str]}`, built with
   `turn_response()` in `app/integrations/research_engine/engine.py`. Failures are still raised, and the worker still owns the
   terminal state.
2. **Upstream output controls.** Native controls only:
   - ODR: a response-style instruction is added to the user message, which ODR's final-report prompt explicitly takes into
     account. The vendored prompts are not patched.
   - GPT-Researcher: `write_report(custom_prompt=...)`, its supported prompt override.
   - STORM: it has no output control and always writes a Wikipedia-style article, so it returns `format="article"`. This is a
     documented limitation; no summarizer is added.
3. **Worker.** It persists `text` to `ConversationTurn.assistant_message` and publishes `turn.completed` / `done` with
   `assistant_message`, `evidence` (id, url, title, excerpt, retriever, provenance) and `routing`. It creates **no**
   `ResearchReport` and **no** candidate. Evidence stays in `research_evidence`, linked through the run and the turn.
4. **StudyReportCompiler** (`app/services/research/study_report.py`), invoked only by:
   - `POST /workspaces/{ws}/conversations/{conv}/study-report`, or
   - a turn whose message is an explicit compile request (`is_study_report_request`).

   It gathers the conversation's ordered completed turns, the cited Ground sources with their relevant passages, the
   `ResearchEvidence` of the conversation's runs, and the conversation's scratchpad findings and hypotheses. It builds a numbered
   citation catalog and makes **one** bounded LLM call. Citation markers outside the catalog are stripped and reported as
   warnings, and the References section is generated from the catalog, never by the LLM. It does not launch research.
5. **Schema (minimum).** `research_reports` and `research_artifacts` get `run_id` nullable plus `workspace_id` and
   `conversation_id`, and `research_reports` gets `scope` (`run` | `study_session`). Check constraints require the right anchor
   for each scope. Candidate review scopes by run *or* by the artifact's own `workspace_id`.
6. Nothing is auto-promoted. Ground mode is unchanged and stays grounded in canonical sources.

## Out of scope

Rewriting upstream prompts; a Neosis summarizer for STORM; semantic claim verification.
