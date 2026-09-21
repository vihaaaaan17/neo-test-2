# NeosisLM Phase B/C Implementation Handoff

## Summary

Implemented tickets 05-15 from Phase B (Evidence) and Phase C (Upstream Capability Boundaries).

## Key Changes

1. **RetrieverRegistry Interface**
   - Created central retriever management with policy enforcement.
   - Implemented `ResearchSourceResult` and `ResearchRetrievalPolicy`.
   - Added `RetrieverRegistry` class.

2. **Web Retriever Normalization**
   - Standardized web retrieval results.
   - Implemented fingerprinting and provenance tracking.
   - Added workspace validation.

3. **Academic Retriever**
   - Added academic search capability.
   - Implemented arXiv and PubMed integration.
   - Added evidence normalization.

4. **MCP Capability Boundary**
   - Added MCP policy enforcement.
   - Implemented secure credential handling.
   - Added call budget tracking.

5. **GPT Researcher Capability ACL**
   - Implemented structured retrieval results.
   - Added Neosis adapter layer.
   - Added usage accounting.

6. **STORM Formal Deferral**
   - Created ADR for STORM deferral.
   - Added `STORM_ENABLED: bool = False`.
   - Documented architectural decision.

7. **Provenance Model Strengthening**
   - Enhanced `ResearchEvidence` with provenance fields.
   - Added `source_resolution_status`.
   - Implemented deterministic validation.

8. **Claim/Citation Mapping & Audit**
   - Added `provenance_version` and `status` to `ResearchReport`.
   - Implemented `audit_claim_citations` method.
   - Added cross-workspace/cross-run validation.

9. **Durable ResearchEvent Persistence**
   - Added `sequence` column to `ResearchEvent`.
   - Modified `create_event` for atomic writes.
   - Added Redis Pub/Sub publication.

10. **AsyncPostgresSaver Integration**
    - Replaced `MemorySaver` with `AsyncPostgresSaver`.
    - Added feature flag for local development.
    - Added PostgreSQL DSN configuration.

11. **Retry Attempt Model**
    - Added `current_attempt_id` to `ResearchRun`.
    - Updated `create_run` to generate attempt IDs.
    - Added attempt tracking to lifecycle service.

## Verification

- All tickets have passed acceptance criteria.
- Comprehensive tests implemented and verified.
- Architecture invariants maintained.

## Next Steps

- Phase D: Durable Execution and Event Model.
- Phase E: Resource Governance.
