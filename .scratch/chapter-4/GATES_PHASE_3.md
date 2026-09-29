# Chapter 4 Phase 3 Gate Ledger

## Status
- **Phase**: 3 (Promotion, Provenance, Derivation & Workspace Versioning)
- **Status**: Completed (Tickets 01-04 Verified Green)
- **Unit Tests**: 104/104 passing

## Tickets
- [x] Ticket 01: Candidate Lifecycle Models, Migration & Repositories (`.scratch/chapter-4/phase-3-issues/01-candidate-lifecycle-models-and-repositories.md`)
- [x] Ticket 02: Typed Schemas, Derivation & Deterministic AST Verification (`.scratch/chapter-4/phase-3-issues/02-typed-schemas-derivation-and-verification.md`)
- [x] Ticket 03: Promotion Service, Output KG Gate & REST API (`.scratch/chapter-4/phase-3-issues/03-promotion-service-output-graph-gate-and-api.md`)
- [x] Ticket 04: Timeline Epoch Rollback Fence & E2E Verification (`.scratch/chapter-4/phase-3-issues/04-timeline-epoch-rollback-fence-and-verification.md`)

## Invariant Ledger
- [x] Invariant 1: No auto-promotion to `KnowledgeMemory` or Neo4j Output KG on run completion.
- [x] Invariant 2: Memory promotion and Output KG promotion are independently controllable.
- [x] Invariant 3: Rejection is durable and audit-preserved; never deletes execution logs/evidence.
- [x] Invariant 4: Acceptance is strictly idempotent.
- [x] Invariant 5: Provenance is reconstructable with typed `ProvenanceRef` and fail-closed isolation.
- [x] Invariant 6: Workspace rollback increments `timeline_epoch`; stale workers blocked from mutating active timeline.
- [x] Invariant 7: Derived calculations evaluated deterministically with AST whitelist and resource bounds.
