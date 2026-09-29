import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.schemas.graph import ProvenanceRef, ProvenanceBundle
from app.services.research.derivation import DerivationService, CrossWorkspaceBoundaryError
from app.services.research.verification import VerificationResult


@pytest.mark.asyncio
async def test_provenance_lineage_resolution_all_entity_types():
    """
    Provenance validation successfully resolves all 7 supported entity types
    when they belong to the specified workspace.
    """
    workspace_id = uuid4()

    refs = [
        ProvenanceRef(ref_type="source", ref_id=uuid4()),
        ProvenanceRef(ref_type="source_snapshot", ref_id=uuid4()),
        ProvenanceRef(ref_type="block", ref_id=uuid4()),
        ProvenanceRef(ref_type="research_evidence", ref_id=uuid4()),
        ProvenanceRef(ref_type="research_artifact", ref_id=uuid4()),
        ProvenanceRef(ref_type="knowledge_memory", ref_id=uuid4()),
        ProvenanceRef(ref_type="conversation_turn", ref_id=uuid4()),
    ]

    session = AsyncMock()
    # Mock database returning valid results for all 7 queries
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = uuid4()
    session.execute.return_value = mock_res

    derivation_svc = DerivationService(session)
    valid = await derivation_svc.validate_provenance_lineage(workspace_id, refs)

    assert valid is True
    assert session.execute.call_count == 7


@pytest.mark.asyncio
async def test_provenance_lineage_rejects_cross_workspace_reference():
    """
    Provenance validation fails closed (raises CrossWorkspaceBoundaryError)
    if any reference belongs to a different workspace.
    """
    workspace_a = uuid4()
    foreign_ref_id = uuid4()

    refs = [
        ProvenanceRef(ref_type="research_evidence", ref_id=foreign_ref_id),
    ]

    session = AsyncMock()
    # Mock query returning None (not found in workspace_a)
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_res

    derivation_svc = DerivationService(session)

    with pytest.raises(CrossWorkspaceBoundaryError) as exc_info:
        await derivation_svc.validate_provenance_lineage(workspace_a, refs)

    assert f"research_evidence:{foreign_ref_id}" in str(exc_info.value)
    assert "does not belong to workspace" in str(exc_info.value)


@pytest.mark.asyncio
async def test_provenance_lineage_rejects_missing_entity():
    """
    Provenance validation fails closed if a referenced entity does not exist at all.
    """
    workspace_id = uuid4()
    missing_id = uuid4()

    refs = [
        ProvenanceRef(ref_type="block", ref_id=missing_id),
    ]

    session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_res

    derivation_svc = DerivationService(session)

    with pytest.raises(CrossWorkspaceBoundaryError) as exc_info:
        await derivation_svc.validate_provenance_lineage(workspace_id, refs)

    assert f"block:{missing_id}" in str(exc_info.value)


def test_build_provenance_bundle():
    """
    Building a provenance bundle maps typed refs, populates derived_from_refs legacy list,
    and attaches calculation and verification outputs.
    """
    ref1 = ProvenanceRef(ref_type="source", ref_id=uuid4(), locator="page:12")
    ref2 = ProvenanceRef(ref_type="research_evidence", ref_id=uuid4())

    session = AsyncMock()
    svc = DerivationService(session)

    bundle = svc.build_provenance_bundle(
        refs=[ref1, ref2],
        calculation="100 * (1.15 ** 3)",
        verification_result=VerificationResult(
            status="verified",
            evaluated_value=152.0875,
            reason={"method": "ast_arithmetic_verifier"}
        )
    )

    assert len(bundle.derived_from) == 2
    assert bundle.derived_from_refs == [ref1.ref_id, ref2.ref_id]
    assert bundle.calculation == "100 * (1.15 ** 3)"
    assert bundle.verification_status == "verified"
    assert bundle.verification_details["method"] == "ast_arithmetic_verifier"


@pytest.mark.asyncio
async def test_normalize_derivation_rejects_invalid_provenance_in_payload():
    """
    normalize_derivation fails closed if the candidate payload contains
    provenance pointing to an entity that fails validation.
    """
    workspace_id = uuid4()
    invalid_id = uuid4()

    candidate_dict = {
        "payload": {
            "claim": "Superconductivity transition",
            "provenance": {
                "derived_from": [
                    {"ref_type": "source", "ref_id": str(invalid_id)}
                ]
            }
        }
    }

    session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_res

    derivation_svc = DerivationService(session)

    with pytest.raises(CrossWorkspaceBoundaryError):
        await derivation_svc.normalize_derivation(workspace_id, candidate_dict)
