# Ticket 02: Typed Schemas, Derivation & Deterministic AST Verification

## Summary
Build type-safe candidate schemas, typed provenance models, the deterministic arithmetic verification engine, and derivation services with fail-closed multi-tenancy verification.

## Scope & Changes
1. **`app/schemas/promotion.py`**:
   - `CandidateType`: Enum (`memory_candidate`, `graph_candidate`, `claim_candidate`, `finding_candidate`, `hypothesis_candidate`).
   - `PromotionStatus`: Enum (`pending_review`, `accepted`, `rejected`, `superseded`, `not_promotable`).
   - `VerificationStatus`: Enum (`verified`, `unverified`, `failed`).
   - `CandidatePayload`: Type-specific schemas (e.g., `MemoryCandidatePayload`, `GraphCandidatePayload`, `FindingCandidatePayload`).
   - `PromotionCandidateResponse`: Artifact candidate representation with envelope fields (`artifact_id`, `run_id`, `workspace_id`, `type`, `promotion_status`, `content`, `payload`, `verification_status`, `verification_reason`, `created_at`, `reviewed_at`, `reviewed_by`).
   - `PromotionReviewRequest`: (`decision: Literal["accept", "reject"]`, `review_reason: Optional[str] = None`).
   - `PromotionReviewResponse`: Updated candidate with linked target details.

2. **`app/schemas/graph.py` & `app/schemas/knowledge.py`**:
   - Typed `ProvenanceRef`:
     - `ref_type`: Literal[`"source"`, `"source_snapshot"`, `"block"`, `"research_evidence"`, `"research_artifact"`, `"knowledge_memory"`, `"conversation_turn"`]
     - `ref_id`: `UUID`
     - `locator`: `Optional[str] = None`
   - Update `ProvenanceBundle`:
     - `derived_from`: `List[ProvenanceRef] = Field(default_factory=list)`
     - `derived_from_refs`: Legacy `List[UUID]` preserved for backwards compatibility.
     - `calculation`: `Optional[str] = None`
     - `verification_status`: `Optional[str] = None`
     - `verification_details`: `Optional[Dict[str, Any]] = None`

3. **`app/services/research/verification.py`**:
   - Implement deterministic AST evaluator `DeterministicArithmeticVerifier`:
     - Allowed binary operators: `+`, `-`, `*`, `/`, `**`, `%`, `//`
     - Allowed unary operators: `+`, `-`
     - Allowed comparisons: `==`, `!=`, `<`, `<=`, `>`, `>=`
     - Allowed functions: `round`, `abs`, `min`, `max`, `sum`, `pct_change`
     - Hard limits: Max expression length (500 chars), max AST depth (10), max operations (50), max exponent (10), max magnitude (1e15).
     - Error handling: Raises `ArithmeticVerificationError` on syntax error, unwhitelisted node, or limit violation.
   - `verify_calculation(expression: str, expected_value: float, tolerance: float = 0.001) -> VerificationResult`
   - `verify_claim(claim_data: dict) -> VerificationResult`

4. **`app/services/research/derivation.py`**:
   - `DerivationService`:
     - `build_provenance_bundle(refs: list[ProvenanceRef], calculation: str | None) -> ProvenanceBundle`
     - `validate_provenance_lineage(workspace_id: UUID, refs: list[ProvenanceRef]) -> bool`:
       - Queries underlying tables (`sources`, `research_evidence`, `research_artifacts`, `knowledge_memories`, `conversation_turns`) and verifies `entity.workspace_id == workspace_id`.
       - Fails closed: If any ref is missing or belongs to a different workspace, raises `CrossWorkspaceBoundaryError`.
     - `normalize_derivation(workspace_id: UUID, candidate_dict: dict) -> dict`:
       - Normalizes engine output into canonical candidate payload and executes calculation verification if derivation metadata is present.

## Verification Gates
- [ ] Safe AST evaluator rejects `eval`, `exec`, `import`, attribute access, large exponents, and deep AST trees.
- [ ] Whitelisted math expressions evaluate correctly with tolerance checks.
- [ ] Failed arithmetic verification returns structured failure and does not raise uncaught exceptions.
- [ ] Provenance resolution validates all 7 reference types against workspace ID and rejects cross-workspace entities fail-closed.
