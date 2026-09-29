# Candidate Promotion, Verification and Timeline Fencing

This ADR records the architectural invariants and design decisions for Chapter 4 Phase 3: Candidate Promotion, Provenance, Derivation, and Workspace Versioning.

## Status

Accepted

## Context

In Chapter 3, research completion automatically promoted findings into `KnowledgeMemory` and projected output graphs into Neo4j. This violated the core human-in-the-loop principle: "Research proposes. The user promotes. Canonical state records what was accepted." Furthermore, workspace rollback previously lacked concurrency protection against in-flight background workers, creating the potential for stale executions to corrupt a rolled-back workspace.

## Decisions

### 1. In-Place Candidate Extension on ResearchArtifact
Rather than introducing a separate `PromotionCandidate` table and duplicated metadata, `ResearchArtifact` is extended with lifecycle and verification columns:
- `promotion_status` (`pending_review`, `accepted`, `rejected`, `superseded`, `not_promotable`)
- `reviewed_by`, `reviewed_at`, `review_reason`
- `promoted_target_type`, `promoted_target_id`
- `verification_status`, `verification_reason`, `verification_metadata`

**Rationale**: Preserves a single canonical artifact identity from generation through review and materialization, avoiding multi-table dual writes and sync drift.

### 2. Transactional Materialization & Decoupled Graph Projection
- Acceptance of a `memory_candidate` commits the new `KnowledgeMemory` row in PostgreSQL within the same database transaction as the candidate status transition.
- Acceptance of a `graph_candidate` records acceptance in PostgreSQL and enqueues a background `project_output_graph_job` to project into Neo4j.
- Neo4j is strictly a derived projection, never part of the canonical database transaction. A transient Neo4j failure is an observable, retryable job, never causing the canonical acceptance in PostgreSQL to be lost or rolled back.
- Acceptance is strictly idempotent.

### 3. Authoritative Rollback Fencing via PostgreSQL `timeline_epoch`
- `workspaces.timeline_epoch` serves as the authoritative concurrency fence.
- On rollback, `workspaces` is locked via `SELECT ... FOR UPDATE`, `timeline_epoch` is incremented, and `active_commit_id` is updated atomically.
- Before committing durable state, workers and promotion transactions verify that `workspace.timeline_epoch == expected_epoch`. If mismatched, durable mutations are aborted with `aborted_by_timeline_fence`.
- Historical research runs, tasks, evidence, and reports are never deleted by rollback.

### 4. Deterministic AST Evaluation for Derivation Verification
- Mathematical and derived claims are verified deterministically using Python's `ast` module with an operator and function whitelist (`+`, `-`, `*`, `/`, `**`, `%`, `//`, `round`, `abs`, `min`, `max`, `sum`, `pct_change`).
- Resource limits are strictly enforced: max expression length 500, max AST depth 10, max operation count 50, max exponent 10, max magnitude 1e15.
- Verification failures set `verification_status = 'unverified'` or `'failed'` and preserve the candidate in `pending_review` with structured warning details. Failures never silently approve or discard candidates.

### 5. Fail-Closed Typed Provenance Lineage
- All provenance references use a strongly typed `ProvenanceRef` pointing to one of seven supported entity types.
- Every reference is checked against workspace boundaries. If any referenced entity belongs to another workspace or cannot be resolved, promotion fails closed immediately.
