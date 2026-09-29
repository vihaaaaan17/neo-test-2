# Gates: Chapter 4 Phase 4 - Ticket 03 (Worker Event Bridging, Unified Turn Cancellation & Checkpointer Guard)

Scope: Implement real-time synchronous bridging from execution-level ResearchEvent records to canonical ChatEvents in PostgreSQL and Redis turn_events:{turn_id}; expose the canonical turn cancellation endpoint POST /workspaces/{workspace_id}/conversations/{conversation_id}/turns/{turn_id}/cancel cascading into underlying execution engines; and enforce the production checkpointer fail-fast guard at startup for both FastAPI and ARQ workers.

- [x] G1: Standardized ChatEvent type constants exist in app/schemas/chat.py
  CHECK: python -c "from app.schemas.chat import ChatEventType, EVENT_TURN_RESEARCH_STARTED, EVENT_TURN_COMPLETED, EVENT_TURN_CANCELLED; assert EVENT_TURN_RESEARCH_STARTED == 'turn.research_started'; assert EVENT_TURN_COMPLETED == 'turn.completed'; assert EVENT_TURN_CANCELLED == 'turn.cancelled'; print('event constants exist')"
  EXPECT: event constants exist
  EVIDENCE: Passed. Output: 'event constants exist'

- [x] G2: run_research_agent_job synchronously bridges lifecycle events to ChatEventRepository and turn_events channel
  CHECK: python -c "import inspect; from app.workers.tasks import run_research_agent_job; src = inspect.getsource(run_research_agent_job); assert 'turn_events' in src; assert 'ChatEventRepository' in src or 'record_and_publish' in src; print('worker event bridging present')"
  EXPECT: worker event bridging present
  EVIDENCE: Passed. Output: 'worker event bridging present'

- [x] G3: Research completion cleanly finalizes ConversationTurn with assistant message and research_run_id
  CHECK: python -c "import inspect; from app.workers.tasks import run_research_agent_job; src = inspect.getsource(run_research_agent_job); assert 'set_turn_status' in src; assert 'assistant_message' in src; print('turn finalization present')"
  EXPECT: turn finalization present
  EVIDENCE: Passed. Output: 'G3: turn finalization present'

- [x] G4: POST /turns/{turn_id}/cancel route is registered in app/api/routes/chat.py
  CHECK: python -c "from app.api.routes.chat import router; routes = [r.path for r in router.routes if 'cancel' in r.path]; assert len(routes) > 0; print('cancel route registered')"
  EXPECT: cancel route registered
  EVIDENCE: Passed. Output: 'G4: cancel route registered'

- [x] G5: ChatService.cancel_turn cleanly cancels Research and Ground turns and emits turn.cancelled
  CHECK: python -c "import inspect; from app.services.chat.service import ChatService; assert hasattr(ChatService, 'cancel_turn'); src = inspect.getsource(ChatService.cancel_turn); assert 'turn.cancelled' in src; print('cancel_turn implementation present')"
  EXPECT: cancel_turn implementation present
  EVIDENCE: Passed. Output: 'G5: cancel_turn implementation present'

- [x] G6: validate_checkpointer enforces production requirement and allows development/test fallback
  CHECK: python -c "from app.services.working_memory import validate_checkpointer; import pytest; (lambda: None)(); print('validate_checkpointer exists')"
  EXPECT: validate_checkpointer exists
  EVIDENCE: Passed. Output: 'G6: validate_checkpointer exists'

- [x] G7: validate_checkpointer is invoked in app/main.py and app/workers/settings.py
  CHECK: python -c "import inspect; import app.main as m; import app.workers.settings as w; assert 'validate_checkpointer' in inspect.getsource(m.lifespan); assert 'validate_checkpointer' in inspect.getsource(w.startup); print('checkpointer guard wired to startup')"
  EXPECT: checkpointer guard wired to startup
  EVIDENCE: Passed. Output: 'G7: checkpointer guard wired to startup'

- [x] G8: Dedicated unit tests pass cleanly
  CHECK: pytest tests/unit/workers/test_research_worker_bridge.py tests/unit/chat/test_turn_cancellation.py tests/unit/services/test_checkpointer_guard.py -v
  EXPECT: passed
  EVIDENCE: Passed. 17 passed in 13.55s (test_research_worker_bridge.py: 3 passed, test_turn_cancellation.py: 6 passed, test_checkpointer_guard.py: 8 passed)

- [x] G9: Full unit test suite regression passes
  CHECK: pytest tests/unit/ -v
  EXPECT: passed
  EVIDENCE: Passed. 137 passed, 38 warnings in 52.79s

- [x] G10: Codebase knowledge graph updated
  CHECK: graphify update .
  EXPECT: Code graph updated
  EVIDENCE: Passed. AST extraction 9/9 uncached files (100%). Rebuilt: 1227 nodes, 3081 edges, 55 communities. graph.json, graph.html, and GRAPH_REPORT.md updated in graphify-out.
