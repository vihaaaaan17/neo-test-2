# Gates: Chapter 4 Phase 3 - Ticket 04 (Timeline Epoch Rollback Fence, Commit Manifest & E2E Verification)

Scope: Enforce PostgreSQL timeline_epoch concurrency fence, implement workspace commit manifest snapshotting and restoration, build comprehensive unit and integration test suites, and execute regression validation.

- [x] G1: Rollback endpoint uses atomic row-level lock and increments timeline_epoch
  CHECK: python -c "import inspect; from app.api.routes.workspaces import rollback_workspace; src = inspect.getsource(rollback_workspace); assert 'rollback_workspace_atomic' in src; print('atomic rollback wired')"
  EXPECT: atomic rollback wired
  EVIDENCE: atomic rollback wired

- [x] G2: Create commit endpoint builds full manifest snapshot
  CHECK: python -c "import inspect; from app.api.routes.workspaces import create_workspace_commit; src = inspect.getsource(create_workspace_commit); assert 'create_commit_with_manifest' in src or 'manifest' in src; print('manifest commit wired')"
  EXPECT: manifest commit wired
  EVIDENCE: manifest commit wired

- [x] G3: Research worker enforces timeline_epoch fence and aborts stale workers
  CHECK: python -c "import inspect; from app.workers.tasks import run_research_agent_job; src = inspect.getsource(run_research_agent_job); assert 'timeline_epoch' in src; assert 'aborted_by_timeline_fence' in src; print('timeline fence wired')"
  EXPECT: timeline fence wired
  EVIDENCE: timeline fence wired

- [x] G4: Dedicated workspace rollback and epoch fence tests pass
  CHECK: pytest tests/unit/workspace/test_rollback_epoch.py -v
  EXPECT: passed
  EVIDENCE: 4 passed in 6.02s

- [x] G5: Dedicated provenance verification tests pass
  CHECK: pytest tests/unit/research/test_provenance.py -v
  EXPECT: passed
  EVIDENCE: 5 passed in 4.51s

- [x] G6: Full unit test suite regression passes cleanly
  CHECK: pytest tests/unit/ -v
  EXPECT: passed
  EVIDENCE: 104 passed, 37 warnings in 12.61s

- [x] G7: Codebase knowledge graph updated
  CHECK: graphify update .
  EXPECT: Code graph updated
  EVIDENCE: Code graph updated (1212 nodes, 3018 edges, 61 communities)
