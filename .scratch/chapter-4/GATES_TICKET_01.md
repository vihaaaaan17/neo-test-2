# Gates: Chapter 4 Phase 3 - Ticket 01 (Candidate Lifecycle Models, Migration & Repositories)

Scope: Extend ResearchArtifact, Workspace, WorkspaceCommit, and ResearchRun models, create Alembic migration, and implement candidate lifecycle and atomic rollback repository operations.

- [x] G1: Models define Phase 3 lifecycle, epoch, manifest, and base commit fields
  CHECK: python -c "from app.models.research import ResearchArtifact, ResearchRun; from app.models.workspace import Workspace, WorkspaceCommit; assert hasattr(ResearchArtifact, 'promotion_status'); assert hasattr(ResearchArtifact, 'verification_status'); assert hasattr(ResearchRun, 'base_commit_id'); assert hasattr(Workspace, 'timeline_epoch'); assert hasattr(WorkspaceCommit, 'manifest'); print('models ok')"
  EXPECT: models ok
  EVIDENCE: Output: models ok (Exit Code 0)

- [x] G2: Migration f7a8b9c0d1e2 compiles and defines valid upgrade/downgrade chains
  CHECK: python -c "import importlib.util; spec = importlib.util.spec_from_file_location('mig', 'alembic/versions/f7a8b9c0d1e2_add_phase3_promotion_lifecycle_and_timeline_epoch.py'); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); assert m.revision == 'f7a8b9c0d1e2'; assert m.down_revision == 'e6f7a8b9c0d1'; print('migration ok')"
  EXPECT: migration ok
  EVIDENCE: Output: migration ok (Exit Code 0)

- [x] G3: ResearchRepository implements candidate listing, decision, target linking, and verification methods
  CHECK: python -c "from app.repositories.research import ResearchRepository; assert hasattr(ResearchRepository, 'list_candidates_by_status'); assert hasattr(ResearchRepository, 'get_candidate_for_review'); assert hasattr(ResearchRepository, 'set_candidate_decision'); assert hasattr(ResearchRepository, 'link_candidate_target'); assert hasattr(ResearchRepository, 'set_candidate_verification'); print('research repo ok')"
  EXPECT: research repo ok
  EVIDENCE: Output: research repo ok (Exit Code 0)

- [x] G4: WorkspaceRepository implements atomic rollback with epoch increment, verification, and manifest commit creation
  CHECK: python -c "from app.repositories.workspace import WorkspaceRepository; assert hasattr(WorkspaceRepository, 'create_commit_with_manifest'); assert hasattr(WorkspaceRepository, 'rollback_workspace_atomic'); assert hasattr(WorkspaceRepository, 'verify_timeline_epoch'); print('workspace repo ok')"
  EXPECT: workspace repo ok
  EVIDENCE: Output: workspace repo ok (Exit Code 0)

- [x] G5: Dedicated unit tests for candidate lifecycle and atomic rollback pass
  CHECK: pytest tests/unit/research/test_lifecycle_repository.py tests/unit/workspace/test_workspace_atomic_rollback.py -v
  EXPECT: passed
  EVIDENCE: 10 passed in 4.60s (Exit Code 0)

- [x] G6: Full unit test suite regression passes
  CHECK: pytest tests/unit/ -v
  EXPECT: passed
  EVIDENCE: 67 passed, 34 warnings in 18.25s (Exit Code 0)
