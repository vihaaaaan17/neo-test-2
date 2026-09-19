# 05: Phase 2 Research Service Coordinator

**What to build:** 
The central coordinator `app/services/research/service.py` that implements the explicit memory and graph promotion boundaries. It explicitly prevents research outputs from automatically becoming Memory or Graph truths without going through `MemoryRouterService` and `GraphRepository`.

**Blocked by:** 03 (03-lifecycle-and-event-service.md), 04 (04-normalization-and-provenance-services.md)

**Status:** ready-for-agent

- [ ] Create `app/services/research/service.py`.
- [ ] Implement memory promotion logic: querying `ResearchArtifact` records of type `memory_candidate` and dispatching them to `MemoryRouterService.route_to_memory`.
- [ ] Implement graph promotion logic: querying `ResearchArtifact` records of type `graph_candidate` and dispatching them to `GraphRepository.project_output_graph`.
- [ ] Write integration tests verifying that candidate artifacts are successfully promoted to the existing memory and graph backends without bypassing their respective schemas.
