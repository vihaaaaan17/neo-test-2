# Gates: Chapter 4 Phase 4 - Ticket 04 (Canonical Route Delegation & End-to-End Integration Verification)

Scope: Delegate all legacy routes (POST /workspaces/{id}/research, POST /workspaces/{id}/ask) to canonical ChatService with RFC 8288 deprecation headers; confirm dead placeholder paths are retired; and implement the comprehensive Phase 4 end-to-end integration test suite (test_ground_research_ground.py, test_research_promotion.py, test_unified_turn_stream.py, test_cancellation_and_fence.py) followed by full regression verification.

- [x] G1: POST /workspaces/{workspace_id}/research in app/api/routes/workspaces.py delegates to ChatService.submit_turn
  CHECK: python -c "import inspect; from app.api.routes.workspaces import start_research; src = inspect.getsource(start_research); assert 'ChatService' in src; assert 'submit_turn' in src; assert 'Deprecation' in src; print('workspace research route delegates to ChatService')"
  EXPECT: workspace research route delegates to ChatService
  EVIDENCE: verified: output "workspace research route delegates to ChatService", RFC 8288 Deprecation and Link headers attached, backward-compatible {job_id, run_id, turn_id, status: "accepted"} payload returned.

- [x] G2: POST /workspaces/{workspace_id}/ask in app/api/routes/workspaces.py delegates to ChatService.submit_turn
  CHECK: python -c "import inspect; from app.api.routes.workspaces import ask_ground_mode; src = inspect.getsource(ask_ground_mode); assert 'ChatService' in src; assert 'submit_turn' in src; assert 'Deprecation' in src; print('ask route delegates to ChatService')"
  EXPECT: ask route delegates to ChatService
  EVIDENCE: verified: output "ask route delegates to ChatService", RFC 8288 Deprecation and Link headers attached, delegates to ChatService.submit_turn(mode="ground").

- [x] G3: Orphaned enqueue_research_job function is removed from app/api/routes/research.py
  CHECK: python -c "import app.api.routes.research as r; assert not hasattr(r, 'enqueue_research_job'); print('enqueue_research_job absent')"
  EXPECT: enqueue_research_job absent
  EVIDENCE: verified: output "enqueue_research_job absent", dead placeholder function retired.

- [x] G4: E2E Ground -> Research -> Ground test verifies strict Ground isolation (zero research contamination)
  CHECK: pytest tests/e2e/test_ground_research_ground.py -v
  EXPECT: passed
  EVIDENCE: verified: 3 passed in 5.00s. Confirms Ground turns 1 and 3 receive 0 research evidence, reject ResearchContext, and generate zero knowledge candidates or graph mutations.

- [x] G5: E2E Research -> Promotion test verifies candidate review, acceptance materialization, subsequent ingestion, and rejection audit
  CHECK: pytest tests/e2e/test_research_promotion.py -v
  EXPECT: passed
  EVIDENCE: verified: 3 passed in 5.68s. Confirms review endpoint lists candidates, accept materializes KnowledgeMemory/syncs graph, Ground turn consumes accepted memory, and reject records audit trail without materialization.

- [x] G6: E2E Unified Turn Stream test verifies SSE live streaming and PostgreSQL catchup replay
  CHECK: pytest tests/e2e/test_unified_turn_stream.py -v
  EXPECT: passed
  EVIDENCE: verified: 3 passed in 4.91s. Confirms unified SSE stream emits token/answer/milestone events and matches database replay sequence after connection drop.

- [x] G7: E2E Cancellation & Fence test verifies unified turn cancellation and worker epoch fencing
  CHECK: pytest tests/e2e/test_cancellation_and_fence.py -v
  EXPECT: passed
  EVIDENCE: verified: 5 passed in 9.75s. Confirms in-flight Ground task cancellation, Research cooperative pub/sub cancellation signal, worker epoch fence aborts stale run without state mutation, double-cancel idempotency, and terminal state HTTP 400 guard.

- [x] G8: All dedicated Phase 4 E2E tests pass cleanly together
  CHECK: pytest tests/e2e/ -v
  EXPECT: passed
  EVIDENCE: verified: 14 passed in 8.92s across all 4 dedicated E2E test suites.

- [x] G9: Full unit and integration regression test suite passes with 0 regressions
  CHECK: pytest tests/unit/ tests/e2e/ -v
  EXPECT: passed
  EVIDENCE: verified: 162 passed in 47.19s across full unit and e2e test suite with 0 regressions.

- [x] G10: Codebase knowledge graph updated
  CHECK: graphify update .
  EXPECT: Code graph updated
  EVIDENCE: verified: graphify update . rebuilt 1227 nodes, 3087 edges, 59 communities with 0 errors.
