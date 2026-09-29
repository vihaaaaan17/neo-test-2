import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.schemas.graph import ProvenanceRef
from app.services.research.derivation import DerivationService, CrossWorkspaceBoundaryError
from app.services.research.verification import VerificationResult


def test_build_provenance_bundle():
    session = AsyncMock()
    service = DerivationService(session)

    id1 = uuid4()
    id2 = uuid4()
    refs = [
        ProvenanceRef(ref_type="research_evidence", ref_id=id1),
        ProvenanceRef(ref_type="knowledge_memory", ref_id=id2, locator="p.4"),
    ]
    v_res = VerificationResult(
        status="verified",
        computed_value=42.0,
        expected_value=42.0,
        tolerance=0.001,
        reason={"match": True}
    )

    bundle = service.build_provenance_bundle(refs, calculation="21 * 2", verification_result=v_res)
    assert len(bundle.derived_from) == 2
    assert bundle.derived_from_refs == [id1, id2]
    assert bundle.calculation == "21 * 2"
    assert bundle.verification_status == "verified"
    assert bundle.verification_details == {"match": True}


@pytest.mark.asyncio
async def test_validate_provenance_lineage_success():
    workspace_id = uuid4()
    ev_id = uuid4()

    session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = ev_id
    session.execute.return_value = mock_res

    service = DerivationService(session)
    refs = [ProvenanceRef(ref_type="research_evidence", ref_id=ev_id)]

    is_valid = await service.validate_provenance_lineage(workspace_id, refs)
    assert is_valid is True


@pytest.mark.asyncio
async def test_validate_provenance_lineage_cross_workspace_rejected():
    workspace_a = uuid4()
    ev_id = uuid4()

    session = AsyncMock()
    # Mock returns None because the evidence is in Workspace B, not Workspace A
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_res

    service = DerivationService(session)
    refs = [ProvenanceRef(ref_type="research_evidence", ref_id=ev_id)]

    with pytest.raises(CrossWorkspaceBoundaryError, match="invalid or does not belong to workspace"):
        await service.validate_provenance_lineage(workspace_a, refs)


@pytest.mark.asyncio
async def test_normalize_derivation_executes_verification_and_builds_bundle():
    workspace_id = uuid4()
    ev_id = uuid4()

    session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = ev_id
    session.execute.return_value = mock_res

    service = DerivationService(session)

    candidate_dict = {
        "type": "claim_candidate",
        "payload": {
            "claim": "Calculated increase is 25%",
            "evidence_refs": [str(ev_id)],
            "derivation": {
                "expression": "pct_change(100, 125)",
                "expected_value": 25.0,
                "tolerance": 0.01
            }
        }
    }

    normalized = await service.normalize_derivation(workspace_id, candidate_dict)

    assert normalized["verification_status"] == "verified"
    assert normalized["verification_reason"]["match"] is True
    assert "provenance" in normalized["payload"]
    assert normalized["payload"]["provenance"]["calculation"] == "pct_change(100, 125)"
    assert len(normalized["payload"]["provenance"]["derived_from"]) == 1
