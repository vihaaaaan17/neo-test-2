import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from fastapi import HTTPException
from app.models.research import ResearchRun, ResearchArtifact
from app.models.workspace import Workspace
from app.models.knowledge import KnowledgeMemory
from app.schemas.research import ResearchRunResponse
from app.schemas.graph import OutputGraph, OutputGraphNode, OutputGraphEdge
from app.repositories.graph import GraphRepository
from app.services.research.promotion import (
    PromotionService,
    InvalidCandidateTypeError,
    TimelineEpochFencedError,
    InvalidPayloadError,
)
from app.api.routes.promotions import accept_promotion
from app.workers.tasks import project_output_graph_job, sync_knowledge_to_graph_job


# ============================================================================
# Gate 1: ResearchRun schema and Alembic migration include timeline_epoch
# ============================================================================

def test_research_run_schema_and_migration():
    # 1. Model inspection
    assert hasattr(ResearchRun, "timeline_epoch")
    col = ResearchRun.__table__.columns["timeline_epoch"]
    assert str(col.type) == "INTEGER"
    assert not col.nullable

    # 2. Schema inspection
    response_schema = ResearchRunResponse(
        run_id=uuid4(),
        workspace_id=uuid4(),
        owner_id=uuid4(),
        objective="Test Objective",
        status="pending",
        engine="open_deep_research",
        timeline_epoch=3,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    assert response_schema.timeline_epoch == 3

    # Default value check
    response_default = ResearchRunResponse(
        run_id=uuid4(),
        workspace_id=uuid4(),
        owner_id=uuid4(),
        objective="Test Objective",
        status="pending",
        engine="open_deep_research",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    assert response_default.timeline_epoch == 1

    # 3. Alembic migration verification
    import alembic.config
    import alembic.script
    alembic_cfg = alembic.config.Config("alembic.ini")
    script = alembic.script.ScriptDirectory.from_config(alembic_cfg)
    # The migration that introduces timeline_epoch (not whatever the current head is).
    head_rev = "f7a8b9c0d1e2"
    head_step = script.get_revision(head_rev)
    assert head_step is not None
    # Verify migration file content contains timeline_epoch on research_runs
    with open(head_step.path, "r", encoding="utf-8") as f:
        mig_content = f.read()
    assert "timeline_epoch" in mig_content
    assert "research_runs" in mig_content


# ============================================================================
# Gate 2: Timeline Epoch Fencing (PromotionService & Workers)
# ============================================================================

@pytest.mark.asyncio
async def test_timeline_epoch_fencing_promotion_service():
    workspace_id = uuid4()
    artifact_id = uuid4()
    run_id = uuid4()
    user_id = uuid4()

    # Workspace at epoch 2 (advanced after rollback)
    mock_ws = Workspace(
        workspace_id=workspace_id,
        owner_id=user_id,
        status="active",
        timeline_epoch=2
    )

    # Candidate created under stale epoch 1
    mock_candidate = ResearchArtifact(
        artifact_id=artifact_id,
        run_id=run_id,
        type="memory_candidate",
        payload={
            "text": "Stale discovery under epoch 1",
            "timeline_epoch": 1,
        },
        promotion_status="pending_review"
    )

    mock_run = ResearchRun(
        run_id=run_id,
        workspace_id=workspace_id,
        owner_id=user_id,
        objective="Objective",
        timeline_epoch=1
    )

    session = AsyncMock()
    # Workspace query returns epoch 2
    ws_result = MagicMock()
    ws_result.scalars.return_value.first.return_value = mock_ws
    session.execute.return_value = ws_result

    repo = MagicMock()
    repo.get_candidate_for_review = AsyncMock(return_value=mock_candidate)
    repo.get_run = AsyncMock(return_value=mock_run)

    promo_svc = PromotionService(
        session=session,
        research_repo=repo,
        arq_pool=AsyncMock()
    )

    with pytest.raises(TimelineEpochFencedError) as exc_info:
        await promo_svc.accept_candidate(workspace_id, artifact_id, user_id)

    assert "aborted_by_timeline_fence" in str(exc_info.value)


@pytest.mark.asyncio
async def test_timeline_epoch_fencing_workers():
    workspace_id = uuid4()
    knowledge_id = uuid4()

    # Workspace at epoch 3 (advanced)
    mock_ws = Workspace(workspace_id=workspace_id, timeline_epoch=3)
    mock_km = KnowledgeMemory(
        knowledge_id=knowledge_id,
        workspace_id=workspace_id,
        owner_id=uuid4(),
        knowledge_type="research_memory",
        content="Test content",
        status="active",
        provenance={"source_refs": []}
    )

    mock_session = AsyncMock()
    # For sync_knowledge_to_graph_job: first execute is KnowledgeMemory, second is Workspace
    km_res = MagicMock()
    km_res.scalars.return_value.first.return_value = mock_km
    ws_res = MagicMock()
    ws_res.scalars.return_value.first.return_value = mock_ws
    mock_session.execute.side_effect = [km_res, ws_res]

    with patch("app.workers.tasks.async_session_maker") as mock_session_maker:
        mock_session_maker.return_value.__aenter__.return_value = mock_session

        # Run with expected_epoch 1 (stale)
        res = await sync_knowledge_to_graph_job({}, knowledge_id=str(knowledge_id), expected_epoch=1)
        assert res["status"] == "aborted_by_timeline_fence"
        assert "advanced" in res["reason"]


# ============================================================================
# Gate 3: Unsupported candidate types rejected (HTTP 400 invalid_candidate_type)
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.parametrize("unsupported_type", [
    "hypothesis_candidate",
    "claim_candidate",
    "finding_candidate",
    "unknown_type"
])
async def test_unsupported_candidate_types_rejected(unsupported_type):
    workspace_id = uuid4()
    artifact_id = uuid4()
    user_id = uuid4()
    run_id = uuid4()

    mock_candidate = ResearchArtifact(
        artifact_id=artifact_id,
        run_id=run_id,
        type=unsupported_type,
        payload={"text": "Some text"},
        promotion_status="pending_review"
    )

    session = AsyncMock()
    repo = MagicMock()
    repo.get_candidate_for_review = AsyncMock(return_value=mock_candidate)

    promo_svc = PromotionService(
        session=session,
        research_repo=repo,
        arq_pool=AsyncMock()
    )

    # 1. Service layer raises InvalidCandidateTypeError
    with pytest.raises(InvalidCandidateTypeError) as exc_info:
        await promo_svc.accept_candidate(workspace_id, artifact_id, user_id)
    assert exc_info.value.detail == "invalid_candidate_type"

    # 2. HTTP route returns 400 Bad Request with detail="invalid_candidate_type"
    mock_ws = Workspace(workspace_id=workspace_id, owner_id=user_id)
    with patch("app.api.routes.promotions.WorkspaceRepository") as mock_ws_repo_cls:
        mock_ws_repo = mock_ws_repo_cls.return_value
        mock_ws_repo.get_workspace = AsyncMock(return_value=mock_ws)

        with pytest.raises(HTTPException) as http_exc:
            await accept_promotion(
                workspace_id=workspace_id,
                artifact_id=artifact_id,
                current_user=user_id,
                session=session,
                service=promo_svc
            )
        assert http_exc.value.status_code == 400
        assert http_exc.value.detail == "invalid_candidate_type"


# ============================================================================
# Gate 4: Candidate payloads validated against Pydantic schemas prior to acceptance
# ============================================================================

@pytest.mark.asyncio
async def test_candidate_payload_pydantic_validation():
    workspace_id = uuid4()
    artifact_id = uuid4()
    user_id = uuid4()
    run_id = uuid4()

    # Memory candidate with invalid empty text/content
    invalid_mem_candidate = ResearchArtifact(
        artifact_id=artifact_id,
        run_id=run_id,
        type="memory_candidate",
        payload={"text": "   ", "content": ""},
        promotion_status="pending_review"
    )

    session = AsyncMock()
    repo = MagicMock()
    repo.get_candidate_for_review = AsyncMock(return_value=invalid_mem_candidate)

    promo_svc = PromotionService(
        session=session,
        research_repo=repo,
        arq_pool=AsyncMock()
    )

    with pytest.raises(InvalidPayloadError) as exc_info:
        await promo_svc.accept_candidate(workspace_id, artifact_id, user_id)
    assert "Invalid memory_candidate payload" in str(exc_info.value)


# ============================================================================
# Gate 5: Background projection jobs enqueued strictly post-transaction commit
# ============================================================================

@pytest.mark.asyncio
async def test_background_projection_post_commit():
    workspace_id = uuid4()
    artifact_id = uuid4()
    user_id = uuid4()
    run_id = uuid4()

    mock_candidate = ResearchArtifact(
        artifact_id=artifact_id,
        run_id=run_id,
        type="memory_candidate",
        payload={"text": "Valid finding for post-commit test"},
        promotion_status="pending_review"
    )

    call_order = []

    session = AsyncMock()
    session.add = MagicMock()
    async def mock_commit():
        call_order.append("db_commit")
    session.commit = AsyncMock(side_effect=mock_commit)

    repo = MagicMock()
    repo.get_candidate_for_review = AsyncMock(return_value=mock_candidate)

    arq_pool = AsyncMock()
    async def mock_enqueue(job_name, **kwargs):
        call_order.append(f"enqueue_{job_name}")
    arq_pool.enqueue_job = AsyncMock(side_effect=mock_enqueue)
    arq_pool.publish = AsyncMock()

    promo_svc = PromotionService(
        session=session,
        research_repo=repo,
        arq_pool=arq_pool
    )

    await promo_svc.accept_candidate(workspace_id, artifact_id, user_id)

    # Strict invariant: db_commit must occur BEFORE enqueue_sync_knowledge_to_graph_job
    assert call_order == ["db_commit", "enqueue_sync_knowledge_to_graph_job"]


# ============================================================================
# Gate 6: Graph topology validation, commit authority, and subgraph tagging
# ============================================================================

@pytest.mark.asyncio
async def test_graph_projection_topology_and_authority():
    workspace_id = uuid4()
    active_commit = uuid4()

    # 1. Malformed topology: empty node ID
    malformed_node_graph = {
        "nodes": [{"id": "", "label": "Concept", "properties": {}}],
        "edges": []
    }
    res1 = await project_output_graph_job({}, workspace_id=str(workspace_id), graph_dict=malformed_node_graph)
    assert res1["status"] == "failed"
    assert res1["error"] == "malformed_graph_topology"
    assert "Node ID cannot be empty" in res1["detail"]

    # 2. Malformed topology: edge endpoints non-existent
    malformed_edge_graph = {
        "nodes": [{"id": "n1", "label": "Concept", "properties": {}}],
        "edges": [{"source_id": "n1", "target_id": "non_existent", "type": "RELATES_TO", "properties": {}}]
    }
    res2 = await project_output_graph_job({}, workspace_id=str(workspace_id), graph_dict=malformed_edge_graph)
    assert res2["status"] == "failed"
    assert res2["error"] == "malformed_graph_topology"
    assert "Edge target endpoint" in res2["detail"]

    # 3. Valid topology but lacks active-commit authority (workspace.active_commit_id is None)
    valid_graph = {
        "nodes": [{"id": "n1", "label": "Concept", "properties": {}}],
        "edges": []
    }
    mock_ws_no_commit = Workspace(workspace_id=workspace_id, active_commit_id=None, timeline_epoch=1)
    mock_session = AsyncMock()
    ws_res = MagicMock()
    ws_res.scalars.return_value.first.return_value = mock_ws_no_commit
    mock_session.execute.return_value = ws_res

    with patch("app.workers.tasks.async_session_maker") as mock_session_maker:
        mock_session_maker.return_value.__aenter__.return_value = mock_session
        res3 = await project_output_graph_job({}, workspace_id=str(workspace_id), graph_dict=valid_graph)
        assert res3["status"] == "rejected"
        assert res3["error"] == "lacks_active_commit_authority"

    # 4. Independent projection with mismatched commit_id
    mock_ws_active = Workspace(workspace_id=workspace_id, active_commit_id=active_commit, timeline_epoch=1)
    ws_res_active = MagicMock()
    ws_res_active.scalars.return_value.first.return_value = mock_ws_active
    mock_session.execute.return_value = ws_res_active

    with patch("app.workers.tasks.async_session_maker") as mock_session_maker:
        mock_session_maker.return_value.__aenter__.return_value = mock_session
        res4 = await project_output_graph_job(
            {},
            workspace_id=str(workspace_id),
            graph_dict=valid_graph,
            commit_id=str(uuid4()) # Mismatched
        )
        assert res4["status"] == "rejected"
        assert res4["error"] == "lacks_active_commit_authority"

    # 5. Authorized projection succeeds and tags commit_id & workspace_id
    with patch("app.workers.tasks.async_session_maker") as mock_session_maker:
        mock_session_maker.return_value.__aenter__.return_value = mock_session
        with patch.object(GraphRepository, "project_output_graph", AsyncMock()) as mock_proj:
            res5 = await project_output_graph_job(
                {},
                workspace_id=str(workspace_id),
                graph_dict=valid_graph,
                commit_id=str(active_commit)
            )
            assert res5["status"] == "completed"
            assert res5["commit_id"] == str(active_commit)
            # Verify project_output_graph was called with commit_id
            assert mock_proj.called
            call_kwargs = mock_proj.call_args[1] if mock_proj.call_args[1] else {}
            call_args = mock_proj.call_args[0]
            # Verify commit_id is passed
            assert call_kwargs.get("commit_id") == active_commit or (len(call_args) >= 3 and call_args[2] == active_commit)
