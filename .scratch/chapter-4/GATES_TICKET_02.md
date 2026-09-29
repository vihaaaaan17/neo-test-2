# Gates: Chapter 4 Phase 3 - Ticket 02 (Typed Schemas, Derivation & Deterministic AST Verification)

Scope: Implement candidate schemas, typed ProvenanceRef, DeterministicArithmeticVerifier with AST safety limits, and DerivationService with fail-closed lineage validation.

- [x] G1: app/schemas/promotion.py compiles and validates candidate types, payloads, and review contracts
  CHECK: python -c "from app.schemas.promotion import PromotionCandidateResponse, PromotionReviewRequest, CandidateType, PromotionStatus, VerificationStatus; print('schemas ok')"
  EXPECT: schemas ok
  EVIDENCE: Output: schemas ok (Exit Code 0)

- [x] G2: app/schemas/graph.py and app/schemas/knowledge.py support typed ProvenanceRef and updated ProvenanceBundle
  CHECK: python -c "from app.schemas.graph import ProvenanceRef, ProvenanceBundle; from uuid import uuid4; p = ProvenanceBundle(derived_from=[ProvenanceRef(ref_type='research_evidence', ref_id=uuid4())]); assert len(p.derived_from) == 1; print('provenance schema ok')"
  EXPECT: provenance schema ok
  EVIDENCE: Output: provenance schema ok (Exit Code 0)

- [x] G3: DeterministicArithmeticVerifier evaluates safe arithmetic, enforces limits, and rejects arbitrary execution
  CHECK: python -c "from app.services.research.verification import DeterministicArithmeticVerifier, verify_calculation; res = verify_calculation('(1.42 / 1.20 - 1) * 100', 18.333, tolerance=0.01); assert res.status == 'verified'; print('verifier ok')"
  EXPECT: verifier ok
  EVIDENCE: Output: verifier ok (Exit Code 0)

- [x] G4: DerivationService validates lineage against workspace boundaries and fails closed on cross-workspace refs
  CHECK: python -c "from app.services.research.derivation import DerivationService, CrossWorkspaceBoundaryError; print('derivation service ok')"
  EXPECT: derivation service ok
  EVIDENCE: Output: derivation service ok (Exit Code 0)

- [x] G5: Dedicated unit tests for verification engine and derivation service pass
  CHECK: pytest tests/unit/research/test_verification.py tests/unit/research/test_derivation.py -v
  EXPECT: passed
  EVIDENCE: 11 passed in 4.47s (Exit Code 0)

- [x] G6: Full unit test suite regression passes
  CHECK: pytest tests/unit/ -v
  EXPECT: passed
  EVIDENCE: 78 passed, 34 warnings in 17.13s (Exit Code 0)
