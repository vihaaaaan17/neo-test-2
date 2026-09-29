# Ticket 02: ODR Research Adapter Context Ingestion & Candidate Emission

**What to build:**
Enable `OpenDeepResearchEngine` to ingest the canonical, token-budgeted `ResearchContext` snapshotted on `ConversationTurn.context_version` without modifying the upstream ODR LangGraph topology. Ensure ODR execution finalizes by emitting structured candidate artifacts (`memory_candidate`, `graph_candidate`) conforming to the Phase 3 candidate envelope in `pending_review` status without auto-promotion.

**Blocked by:** None (can start immediately).

**Status:** completed

## Scope & Changes
1. **`app/integrations/research_engine/open_deep_research/engine.py`**:
   - Update `astream_events` to accept optional `research_context: Optional[dict] = None`.
   - If `research_context` is provided (or loaded from turn `context_version`), format it into an authoritative `RESEARCH CONTEXT AND WORKING STATE` system block:
     - Bounded prior conversation turns
     - Working memory state
     - Active scratchpad entries & hypotheses
     - Accepted knowledge memories
     - Prior research evidence & graph summary
   - Prepend this structured block to the initial user objective message in `initial_state = {"messages": [...]}`.
   - Do NOT modify upstream ODR supervisor, researcher nodes, or research graphs.

2. **Structured Candidate Emission in ODR Finalization**:
   - On `final_report_generation`:
     - Persist full report in `ResearchReport` as canonical report state.
     - Emit candidate artifact in `pending_review` status conforming to Phase 3 candidate envelope (`candidate_type`, `content`, `evidence_refs`, `source_refs`, `proposed_memory_type="research_memory"`, `provenance_version="v2"`).
     - Do NOT call auto-promotion or Neo4j projection.

3. **Verification**:
   - Unit tests verifying `OpenDeepResearchEngine` receives and maps `ResearchContext`.
   - Verification that final report emission creates `pending_review` candidate without auto-promotion.

## Acceptance Criteria
- [x] `OpenDeepResearchEngine.astream_events` accepts and maps canonical `ResearchContext` into initial message state.
- [x] Upstream ODR graph files (`deep_researcher.py`, `configuration.py`, etc.) remain 100% untouched.
- [x] ODR final report generation creates a `memory_candidate` in `pending_review` conforming to Phase 3 envelope.
- [x] Zero automatic promotion to `KnowledgeMemory` or Neo4j Output KG during or after ODR run.
- [x] Dedicated unit tests pass cleanly.
