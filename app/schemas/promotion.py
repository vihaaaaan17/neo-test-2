from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

CandidateType = Literal[
    "memory_candidate",
    "graph_candidate",
    "claim_candidate",
    "finding_candidate",
    "hypothesis_candidate",
]

PromotionStatus = Literal[
    "pending_review",
    "accepted",
    "rejected",
    "superseded",
    "not_promotable",
]

VerificationStatus = Literal[
    "verified",
    "unverified",
    "failed",
]


class DerivationExpression(BaseModel):
    expression: str
    expected_value: Optional[float] = None
    tolerance: float = 0.001
    inputs: Dict[str, float] = Field(default_factory=dict)


class MemoryCandidatePayload(BaseModel):
    text: str
    domain: str = "deep_research"
    confidence: Optional[float] = None
    derivation: Optional[DerivationExpression] = None
    provenance: Optional[Dict[str, Any]] = None


class GraphCandidatePayload(BaseModel):
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    edges: List[Dict[str, Any]] = Field(default_factory=list)
    provenance: Optional[Dict[str, Any]] = None


class ClaimCandidatePayload(BaseModel):
    claim: str
    confidence: Optional[float] = None
    evidence_refs: List[UUID] = Field(default_factory=list)
    derivation: Optional[DerivationExpression] = None


class FindingCandidatePayload(BaseModel):
    finding: str
    supporting_claims: List[str] = Field(default_factory=list)
    derivation: Optional[DerivationExpression] = None
    evidence_refs: List[UUID] = Field(default_factory=list)


class HypothesisCandidatePayload(BaseModel):
    hypothesis: str
    confidence: Optional[float] = None
    tags: List[str] = Field(default_factory=list)


class PromotionCandidateResponse(BaseModel):
    artifact_id: UUID
    run_id: UUID
    workspace_id: Optional[UUID] = None
    type: str
    tags: List[str] = Field(default_factory=list)
    payload: Dict[str, Any]
    promotion_status: str
    reviewed_by: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None
    review_reason: Optional[str] = None
    promoted_target_type: Optional[str] = None
    promoted_target_id: Optional[UUID] = None
    verification_status: Optional[str] = None
    verification_reason: Optional[Dict[str, Any]] = None
    verification_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PromotionReviewRequest(BaseModel):
    decision: Literal["accept", "reject"]
    review_reason: Optional[str] = None


class PromotionReviewResponse(BaseModel):
    artifact_id: UUID
    promotion_status: str
    promoted_target_type: Optional[str] = None
    promoted_target_id: Optional[UUID] = None
    reviewed_at: datetime
    reviewed_by: UUID
    review_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
