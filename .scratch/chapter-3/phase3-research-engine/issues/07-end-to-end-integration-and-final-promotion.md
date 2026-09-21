# 07: End-to-End Integration and Final Promotion

**What to build:** 
Finalize the execution lifecycle. When ODR completes successfully, the adapter normalizes its final report and persists the required `ResearchArtifact` records (`memory_candidate`, `graph_candidate`). The outer worker loop then finalizes the `ResearchRun` state to `COMPLETED` and explicitly triggers `promote_memory_candidates` and `promote_graph_candidates` via the Phase 2 `ResearchService`. Validate the full pipeline from API to final promotion with an integration test.

**Blocked by:** 06: Retries and Context Injection

**Status:** ready-for-agent

- [x] Implement report normalization from ODR output.
- [x] Update worker to call `ResearchService` promotion methods when state reaches `COMPLETED`.
- [x] Write integration test validating the entire Phase 3 flow: `FastAPI -> ResearchService -> Worker -> ODR Adapter -> Retriever -> Postgres -> Memory/Graph`.
