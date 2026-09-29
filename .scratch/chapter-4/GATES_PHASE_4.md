# Chapter 4 Phase 4 Gate Ledger

## Status
- **Phase**: 4 (Unified Execution & Chapter 3 Integration)
- **Status**: Completed (Tickets 01, 02, 03, 04 Completed & Verified)
- **Baseline Unit Tests**: 162/162 passing across all unit and e2e integration suites

## Tickets
- [x] Ticket 01: Ground Execution Adapter & Open Notebook Streaming Integration (`.scratch/chapter-4/phase-4-issues/01-ground-execution-adapter-and-open-notebook-integration.md`)
- [x] Ticket 02: ODR Research Adapter Context Ingestion & Candidate Emission (`.scratch/chapter-4/phase-4-issues/02-odr-research-adapter-context-ingestion-and-candidate-emission.md`)
- [x] Ticket 03: Worker Event Bridging, Unified Turn Cancellation & Production Checkpointer Guard (`.scratch/chapter-4/phase-4-issues/03-worker-event-bridge-unified-cancellation-and-checkpointer-guard.md`)
- [x] Ticket 04: Canonical Route Delegation & End-to-End Integration Verification (`.scratch/chapter-4/phase-4-issues/04-canonical-route-delegation-and-e2e-integration-verification.md`)

## Invariant Ledger
- [x] Invariant 1: Ground executes through canonical `ConversationTurn` using strictly `GroundContext`.
- [x] Invariant 2: Research executes through canonical `ConversationTurn` using `ResearchContext` with `ResearchRun` execution identity.
- [x] Invariant 3: ODR receives Chapter 4 context without modifying upstream ODR LangGraph topology.
- [x] Invariant 4: Research events bridge synchronously into canonical `ChatEvent`s in PostgreSQL and Redis.
- [x] Invariant 5: Canonical turn cancellation cascades cleanly into underlying engines.
- [x] Invariant 6: Production checkpointer strictly requires `AsyncPostgresSaver` and fails fast on startup.
- [x] Invariant 7: Legacy API routes delegate to canonical `ChatService` with deprecation headers.
- [x] Invariant 8: Ground -> Research -> Ground preserves absolute Ground isolation (zero research contamination).
