# Gates: Chapter 4 Phase 3 - Ticket 03 (Promotion Service, Output KG Gate & REST API)

Scope: Implement PromotionService with dual-target independence and idempotency, disarm auto-promotion in worker tasks, enforce Output KG acceptance gating, expose Promotion REST API, and track base_commit_id.

- [x] G1: PromotionService imports cleanly and implements candidate review and materialization methods
  CHECK: python -c "from app.services.research.promotion import PromotionService; assert hasattr(PromotionService, 'accept_candidate'); assert hasattr(PromotionService, 'reject_candidate'); assert hasattr(PromotionService, 'list_candidates'); assert hasattr(PromotionService, 'materialize_memory_candidate'); assert hasattr(PromotionService, 'materialize_graph_candidate'); print('promotion service ok')"
  EXPECT: promotion service ok
  EVIDENCE: promotion service ok

- [x] G2: Worker tasks and research service disarm automatic promotion and Output KG projection on run completion
  CHECK: python -c "import inspect; from app.workers import tasks; src = inspect.getsource(tasks.run_research_agent_job); assert 'promote_memory_candidates' not in src; assert 'promote_graph_candidates' not in src; print('worker auto-promotion disarmed')"
  EXPECT: worker auto-promotion disarmed
  EVIDENCE: worker auto-promotion disarmed

- [x] G3: Promotion API router is defined and registered in FastAPI application
  CHECK: python -c "from app.main import app; paths = app.openapi()['paths']; assert any('/workspaces/{workspace_id}/promotions' in p for p in paths); print('promotion routes registered')"
  EXPECT: promotion routes registered
  EVIDENCE: promotion routes registered

- [x] G4: ChatService attaches workspace active_commit_id as base_commit_id on Research turns
  CHECK: python -c "import inspect; from app.services.chat.service import ChatService; src = inspect.getsource(ChatService._execute_research_turn); assert 'base_commit_id' in src; print('base_commit_id wired')"
  EXPECT: base_commit_id wired
  EVIDENCE: base_commit_id wired

- [x] G5: Dedicated unit tests for PromotionService, dual-target independence, idempotency, and REST API pass
  CHECK: pytest tests/unit/research/test_promotion_service.py tests/unit/api/test_promotions_api.py -v
  EXPECT: passed
  EVIDENCE: 11 passed in 9.35s

- [x] G6: Full unit test suite regression passes
  CHECK: pytest tests/unit/ -v
  EXPECT: passed
  EVIDENCE: 89 passed, 34 warnings in 13.13s
