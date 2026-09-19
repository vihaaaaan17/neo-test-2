# NeosisLM — Chapter 3 Phase 2 Specification

## Problem Statement

The prototype Research Mode currently executes search requests and persists evidence as formatted strings in memory, jumping directly to graph synthesis without maintaining any canonical domain records of what was researched, what evidence was found, where it came from, or what the lineage of the claims are. We need a foundational "research fabric" that acts as the durable system of record for the research domain, allowing us to build out production-ready observability, tracking, deduplication, and provenance.

## Solution

Establish the canonical Neosis research fabric in PostgreSQL. We will create the foundational tables (`ResearchEvidence`, `ResearchArtifact`, `ResearchReport`, `ResearchUsage`, `ResearchEvent`), strict repositories ensuring workspace isolation, and a robust service layer to enforce state machine lifecycle rules and explicitly control promotion boundaries to Memory and Graph projections.

## User Stories

1. As a system operator, I want to track `ResearchRun` and `ResearchTask` lifecycles, so that I have a durable record of all research executions independent of the upstream execution engine.
2. As a system operator, I want `ResearchEvidence` to be a first-class relational entity with a `source_id` link, so that evidence is strictly tracked and deduplicated across tasks.
3. As an application developer, I want all state transitions to go through a `ResearchLifecycleService`, so that invalid transitions (e.g., FAILED -> RESEARCHING) are rejected.
4. As an application developer, I want `ResearchArtifact` records to act as candidates for promotion, so that I can explicitly control when research becomes Memory or Graph projections.
5. As a system operator, I want to track `ResearchUsage`, so that I have accurate accounting for operational economics at the run and task level.
6. As a security reviewer, I want all repository operations to enforce `workspace_id`, so that cross-workspace data leakage is structurally impossible.

## Implementation Decisions

- **Domain Models (`app/models/research.py`)**: All Phase 2 models (`ResearchEvidence`, `ResearchArtifact`, `ResearchReport`, `ResearchUsage`, `ResearchEvent`) will be added to the existing file to maintain domain cohesion.
- **Evidence Source Linkage**: `ResearchEvidence` will have a nullable `source_id` FK. Unresolved sources will leave this null and store raw provenance in a JSONB `provenance` field.
- **Tagging**: We will use `ARRAY(String)` on applicable entities with schema-level Python Enum validation, avoiding a complex relational tagging table.
- **State Machine**: Enforced exclusively via a new `ResearchLifecycleService` (`app/services/research/lifecycle.py`), not inside the repository or API.
- **Repositories**: A unified `app/repositories/research.py` will handle CRUD, strictly enforcing `workspace_id`.
- **Candidates**: Graph and Memory candidates will be stored as `ResearchArtifact` records with explicit `type` tags (`memory_candidate`, `graph_candidate`). Promotion will be handled explicitly by a `ResearchService` coordinator passing data to the existing `MemoryRouterService` and `GraphRepository`.

## Testing Decisions

- **Unit Tests**: Test the state machine transition logic in `ResearchLifecycleService` to ensure invalid transitions raise exceptions. Test evidence fingerprinting and deduplication logic in `ResearchNormalizationService`.
- **Integration Tests**: Verify end-to-end database persistence for the new models without invoking upstream research logic.
- **Security Tests**: Validate that the unified research repository rejects cross-workspace access attempts.

## Out of Scope

- Activating production research traffic.
- Wiring the existing ODR engine to fully populate these tables during live runs (Phase 3).
- UI streaming or final retriever routing.
- Deleting the legacy `ResearchModeOrchestrator`.
