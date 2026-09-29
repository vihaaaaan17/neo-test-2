# Chapter 4 — Phase 3 Specification
## Promotion, Provenance, Derivation & Workspace Versioning

**Repository:** `vihaaaaan17/neo-test-2`  
**Phase Baseline:** Phase 2 complete (37/37 Phase 2 unit tests passing, 57/57 total repository unit tests green)  
**Core Invariant:** *"Research proposes. The user promotes. Canonical state records what was accepted."*

---

## 1. Architectural Decisions Summary (ADR-0003)
1. **Candidate Modeling**: Extend `ResearchArtifact` in-place with lifecycle and verification columns rather than introducing a separate table.
2. **Transaction Sequence**: Commit canonical PostgreSQL acceptance first; Neo4j Output KG projection is asynchronous and retryable via ARQ. Neo4j is strictly a projection.
3. **Rollback Concurrency Fencing**: Authoritative row-locked PostgreSQL `workspaces.timeline_epoch`. Background tasks capture expected epoch; mutations checking in from a stale epoch are aborted (`aborted_by_timeline_fence`).
4. **Deterministic Derivation Verification**: Restricted Python AST evaluator with whitelisted operators/functions and hard resource bounds (depth ≤ 10, ops ≤ 50, exp ≤ 10, mag ≤ 1e15). Failed calculations enter `pending_review` with structured failure reasons; never silently approved or dropped.
5. **Fail-Closed Multi-Tenancy Provenance**: All provenance chains use typed `ProvenanceRef` (7 entity types). Any reference outside the candidate's workspace immediately aborts promotion with a 403 error.

---

## 2. Ticket Breakdown

| Ticket | Scope | Deliverables |
|---|---|---|
| **01** | Models, Migration, Repositories | Extended `ResearchArtifact`, `Workspace`, `WorkspaceCommit`, `ResearchRun`; Alembic migration; candidate querying, status transitions, target linking, and atomic rollback in repositories. |
| **02** | Schemas, Derivation & Verification | `app/schemas/promotion.py`, typed `ProvenanceRef`, `DeterministicArithmeticVerifier` with AST limits, `DerivationService` with fail-closed lineage validation. |
| **03** | Promotion Service & Output KG Gate | `PromotionService`, disarming auto-promotion in worker tasks, Output KG acceptance gate, Promotion REST API (`/workspaces/{workspace_id}/promotions/...`), `ResearchRun.base_commit_id`. |
| **04** | Timeline Epoch Fence & E2E Tests | `timeline_epoch` enforcement in worker finalization, commit manifest snapshotting, comprehensive unit test suites (`test_promotion.py`, `test_verification.py`, `test_provenance.py`, `test_rollback_epoch.py`), regression pass. |

---

## 3. Exit Gates Checklist
- [ ] Research never automatically promotes durable knowledge
- [ ] Research never automatically projects accepted Output KG state
- [ ] Candidate lifecycle is explicit and auditable (`pending_review`, `accepted`, `rejected`, `superseded`)
- [ ] Accept/reject operations are idempotent
- [ ] Memory and graph promotion are independently controllable
- [ ] Candidate payloads are type-validated
- [ ] Provenance is reconstructable across 7 entity types
- [ ] Derived calculations have deterministic AST verification with resource limits
- [ ] Verification failure is explicit (`unverified`/`failed`), never silently treated as success
- [ ] Workspace commits capture approved research state manifests
- [ ] ResearchRun records its `base_commit_id`
- [ ] Rollback increments `timeline_epoch` under row lock
- [ ] Stale workers cannot mutate the post-rollback timeline
- [ ] Historical research execution (runs, evidence, reports) remains intact after rollback
- [ ] Output KG projection requires explicit candidate acceptance
- [ ] Cross-workspace promotion/provenance is rejected fail-closed
- [ ] All Phase 3 integration and unit tests pass
- [ ] Existing regression tests remain green
