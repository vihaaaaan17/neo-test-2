# Detailed Progress Report: NeosisLM Phase B and C Implementation

## Ticket 05: RetrieverRegistry Interface

### **Objective**
- Centralize management of retrievers with policy enforcement.

### **Changes Made**
- **File:** `app/services/research/registry.py`
  - Created `RetrieverRegistry` class to manage retrievers.
  - Implemented `ResearchRetrievalPolicy` for policy enforcement.
  - Added `ResearchSourceResult` schema for standardized results.

### **Logic**
- The `RetrieverRegistry` acts as a central authority for retriever management.
- It enforces policies through `ResearchRetrievalPolicy`, ensuring that retrievers are used according to predefined rules.
- Standardized results are returned using `ResearchSourceResult`, ensuring consistency across different retrievers.

### **Functions**
- `RetrieverRegistry.register_retriever()`: Registers a new retriever.
- `RetrieverRegistry.get_retriever()`: Retrieves a retriever based on policy.
- `ResearchRetrievalPolicy.validate()`: Validates if a retriever can be used.


## Ticket 06: Web Retriever Normalization

### **Objective**
- Standardize web retrieval results and ensure provenance tracking.

### **Changes Made**
- **File:** `app/services/research/web.py`
  - Implemented `WebRetriever` class.
  - Added fingerprinting and provenance tracking.
  - Added workspace validation.

### **Logic**
- The `WebRetriever` fetches web content and normalizes it into a standardized format.
- Each result is fingerprinted to ensure uniqueness and prevent duplicates.
- Workspace validation ensures that retrieved evidence is tied to the correct workspace.

### **Functions**
- `WebRetriever.fetch()`: Fetches web content.
- `WebRetriever.normalize()`: Normalizes fetched content.
- `WebRetriever.validate_workspace()`: Validates workspace access.


## Ticket 07: Academic Retriever

### **Objective**
- Implement academic search capability.

### **Changes Made**
- **File:** `app/services/research/academic.py`
  - Created `AcademicRetriever` class.
  - Implemented arXiv and PubMed integration.
  - Added evidence normalization.

### **Logic**
- The `AcademicRetriever` fetches academic papers and normalizes them into a standardized format.
- Supports multiple academic databases (arXiv, PubMed).
- Ensures that academic evidence follows the same provenance rules as web evidence.

### **Functions**
- `AcademicRetriever.fetch_arxiv()`: Fetches papers from arXiv.
- `AcademicRetriever.fetch_pubmed()`: Fetches papers from PubMed.
- `AcademicRetriever.normalize()`: Normalizes academic content.


## Ticket 08: MCP Capability Boundary

### **Objective**
- Implement MCP policy enforcement and secure credential handling.

### **Changes Made**
- **File:** `app/services/research/mcp.py`
  - Created `MCPRetriever` class.
  - Implemented MCP policy enforcement.
  - Added secure credential handling.
  - Added call budget tracking.

### **Logic**
- The `MCPRetriever` enforces MCP-specific policies and ensures secure credential usage.
- Tracks call budgets to prevent overuse.
- Validates that MCP calls are authorized and within policy limits.

### **Functions**
- `MCPRetriever.query()`: Executes MCP queries.
- `MCPRetriever.enforce_policy()`: Enforces MCP policies.
- `MCPRetriever.track_budget()`: Tracks call budgets.


## Ticket 09: GPT Researcher Capability ACL

### **Objective**
- Implement structured retrieval results and usage accounting.

### **Changes Made**
- **File:** `app/services/research/gpt_researcher.py`
  - Created `GPTResearcherCapability` class.
  - Implemented structured retrieval results.
  - Added Neosis adapter layer.
  - Added usage accounting.

### **Logic**
- The `GPTResearcherCapability` integrates GPT Researcher through a structured adapter.
- Ensures that results are normalized and follow Neosis standards.
- Tracks usage metrics for cost and performance monitoring.

### **Functions**
- `GPTResearcherCapability.execute()`: Executes research tasks.
- `GPTResearcherCapability.normalize_results()`: Normalizes results.
- `GPTResearcherCapability.track_usage()`: Tracks usage metrics.


## Ticket 10: STORM Formal Deferral

### **Objective**
- Document the deferral of STORM integration.

### **Changes Made**
- **File:** `docs/adr/0002-storm-formal-deferral.md`
  - Created ADR for STORM deferral.
- **File:** `app/core/config.py`
  - Added `STORM_ENABLED: bool = False`.

### **Logic**
- The ADR documents the architectural decision to defer STORM integration.
- The configuration flag `STORM_ENABLED` ensures STORM is disabled by default.

### **Files**
- `docs/adr/0002-storm-formal-deferral.md`: ADR document.
- `app/core/config.py`: Configuration flag.


## Ticket 11: Provenance Model Strengthening

### **Objective**
- Enhance provenance tracking for evidence.

### **Changes Made**
- **File:** `app/models/research.py`
  - Added `source_resolution_status` to `ResearchEvidence`.
  - Enhanced provenance tracking.

### **Logic**
- The `source_resolution_status` field ensures that evidence provenance is explicitly tracked.
- Deterministic validation ensures that all evidence is correctly tied to its source.

### **Functions**
- `ResearchEvidence.set_source_resolution_status()`: Sets provenance status.
- `ResearchEvidence.validate_provenance()`: Validates provenance.


## Ticket 12: Claim/Citation Mapping & Audit

### **Objective**
- Implement claim-level citation validation.

### **Changes Made**
- **File:** `app/models/research.py`
  - Added `provenance_version` and `status` to `ResearchReport`.
- **File:** `app/services/research/provenance.py`
  - Implemented `audit_claim_citations()` method.

### **Logic**
- The `provenance_version` and `status` fields ensure that reports are versioned and tracked.
- The `audit_claim_citations()` method validates that all citations in a report resolve to valid evidence within the same workspace and run.

### **Functions**
- `ResearchReport.set_provenance()`: Sets provenance version and status.
- `ResearchProvenanceService.audit_claim_citations()`: Validates citations.


## Ticket 13: Durable ResearchEvent Persistence

### **Objective**
- Ensure all research events are persisted durably.

### **Changes Made**
- **File:** `app/models/research.py`
  - Added `sequence` column to `ResearchEvent`.
- **File:** `app/repositories/research.py`
  - Modified `create_event()` to persist events to PostgreSQL.
  - Added Redis Pub/Sub publication.

### **Logic**
- The `sequence` column ensures events are ordered within a run.
- Events are persisted to PostgreSQL for durability and published to Redis for live updates.

### **Functions**
- `ResearchEvent.set_sequence()`: Sets sequence number.
- `ResearchRepository.create_event()`: Persists and publishes events.


## Ticket 14: AsyncPostgresSaver Integration

### **Objective**
- Replace process-local `MemorySaver` with `AsyncPostgresSaver`.

### **Changes Made**
- **File:** `app/integrations/research_engine/open_deep_research/engine.py`
  - Replaced `MemorySaver` with `AsyncPostgresSaver`.
- **File:** `app/core/config.py`
  - Added `ASYNC_POSTGRES_SAVER_ENABLED` and `POSTGRES_DSN`.

### **Logic**
- `AsyncPostgresSaver` ensures that execution state is persisted to PostgreSQL for durability.
- The feature flag allows local development to continue using `MemorySaver`.

### **Functions**
- `OpenDeepResearchEngine.__init__()`: Initializes the correct checkpointer.


## Ticket 15: Retry Attempt Model

### **Objective**
- Implement attempt tracking for retries.

### **Changes Made**
- **File:** `app/models/research.py`
  - Added `current_attempt_id` to `ResearchRun`.
- **File:** `app/repositories/research.py`
  - Updated `create_run()` to generate and persist `current_attempt_id`.
- **File:** `app/services/research/lifecycle.py`
  - Added `attempt_id` parameter to `transition_run()`.
  - Included `attempt_id` in event payload.

### **Logic**
- The `current_attempt_id` tracks the current execution attempt.
- The `transition_run()` method includes the attempt ID in event payloads for traceability.

### **Functions**
- `ResearchRun.set_attempt_id()`: Sets attempt ID.
- `ResearchRepository.create_run()`: Generates and persists attempt ID.
- `ResearchLifecycleService.transition_run()`: Includes attempt ID in events.


## Verification

- All tickets have passed acceptance criteria.
- Comprehensive tests implemented and verified.
- Architecture invariants maintained.

## Next Steps

- **Phase D:** Durable Execution and Event Model.
- **Phase E:** Resource Governance.