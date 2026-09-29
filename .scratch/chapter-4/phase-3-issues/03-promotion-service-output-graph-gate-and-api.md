# Ticket 03: Promotion Service, Output KG Acceptance Gate & Disarm Auto-Promotion

## Summary
Implement `PromotionService`, disarm automatic promotion and Output KG projection in worker tasks, enforce explicit acceptance gating for Neo4j, and expose the canonical Promotion REST API.

## Scope & Changes
1. **`app/services/research/promotion.py`**:
   - `PromotionService`:
     - `list_candidates(workspace_id: UUID, status: Optional[str] = None, run_id: Optional[UUID] = None) -> list[ResearchArtifact]`
     - `get_candidate(workspace_id: UUID, artifact_id: UUID) -> ResearchArtifact`
     - `accept_candidate(workspace_id: UUID, artifact_id: UUID, user_id: UUID) -> tuple[ResearchArtifact, UUID | None]`:
       - Atomic transaction:
         1. Verify workspace access and candidate existence.
         2. Verify candidate status is `pending_review` (idempotent: if already `accepted`, return existing target).
         3. Validate provenance lineage via `DerivationService` (fail-closed).
         4. Materialize target:
            - If `memory_candidate`: call `materialize_memory_candidate()` to write `KnowledgeMemory` in same DB transaction. Enqueue background `sync_knowledge_to_graph_job`.
            - If `graph_candidate`: call `materialize_graph_candidate()` to record acceptance and enqueue `project_output_graph_job`.
            - If `hypothesis_candidate`: update active scratchpad/hypothesis state.
         5. Set `promotion_status = 'accepted'`, `reviewed_by = user_id`, `reviewed_at = utcnow()`, `promoted_target_type = ...`, `promoted_target_id = ...`.
         6. Commit transaction and emit `promotion.accepted` event.
     - `reject_candidate(workspace_id: UUID, artifact_id: UUID, user_id: UUID, reason: Optional[str] = None) -> ResearchArtifact`:
       - Verify workspace ownership and candidate existence.
       - Set `promotion_status = 'rejected'`, `reviewed_by = user_id`, `reviewed_at = utcnow()`, `review_reason = reason`.
       - Commit transaction; no durable target created, no evidence deleted. Emit `promotion.rejected` event.
     - `materialize_memory_candidate(workspace_id, candidate, owner_id)`
     - `materialize_graph_candidate(workspace_id, candidate)`

2. **Disarm Auto-Promotion in `app/workers/tasks.py` & `app/services/research/service.py`**:
   - In `run_research_agent_job`:
     - Remove `research_service.promote_memory_candidates()` and `promote_graph_candidates()`.
     - Remove un-gated `project_output_graph_job` enqueuing on run completion.
     - Replace with candidate artifact finalization:
       - Validate and normalize candidate artifacts using `DerivationService`.
       - Execute deterministic calculation verification where derivations are present.
       - Set `promotion_status = 'pending_review'`.
       - Commit candidates to PostgreSQL.
       - Emit `promotion.available` event over Redis.

3. **Output KG Acceptance Gate (`app/repositories/graph.py` & ARQ job)**:
   - Ensure `project_output_graph_job` projects graph into Neo4j only when triggered by explicit candidate acceptance.
   - Projecting unaccepted candidates is strictly blocked.

4. **Promotion REST API (`app/api/routes/promotions.py`)**:
   - `GET /workspaces/{workspace_id}/promotions`: List candidates with optional `status` query filter.
   - `GET /workspaces/{workspace_id}/promotions/{artifact_id}`: Candidate detail.
   - `POST /workspaces/{workspace_id}/promotions/{artifact_id}/accept`: Accept candidate.
   - `POST /workspaces/{workspace_id}/promotions/{artifact_id}/reject`: Reject candidate with reason.
   - Register router in `app/main.py`.

5. **`app/services/chat/service.py` & `ResearchRun.base_commit_id`**:
   - During `_submit_research_turn()`, look up workspace's `active_commit_id` and attach as `base_commit_id` when creating `ResearchRun`.

## Verification Gates
- [ ] Completed research run creates candidates in `pending_review` and creates ZERO `KnowledgeMemory` entries.
- [ ] Completed research run does NOT project Neo4j Output KG before acceptance.
- [ ] Calling `/accept` on `memory_candidate` creates exactly one `KnowledgeMemory` record and links `promoted_target_id`.
- [ ] Calling `/accept` again is strictly idempotent and does not create duplicate memories.
- [ ] Calling `/reject` transitions candidate to `rejected` without creating targets or deleting execution history.
- [ ] Memory and graph candidates are independently accepted/rejected.
