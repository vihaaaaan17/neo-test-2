from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal
from uuid import UUID

ProvenanceRefType = Literal[
    "source",
    "source_snapshot",
    "block",
    "research_evidence",
    "research_artifact",
    "knowledge_memory",
    "conversation_turn",
]

class ProvenanceRef(BaseModel):
    ref_type: ProvenanceRefType = Field(..., description="Target entity type for this provenance reference.")
    ref_id: UUID = Field(..., description="UUID of the referenced entity.")
    locator: Optional[str] = Field(default=None, description="Optional block, line, or page locator within the referenced source/evidence.")

class ProvenanceBundle(BaseModel):
    derived_from: List[ProvenanceRef] = Field(default_factory=list, description="Typed references to source entities.")
    derived_from_refs: List[UUID] = Field(default_factory=list, description="Legacy references to internal KnowledgeMemory or chunk IDs.")
    calculation: Optional[str] = Field(default=None, description="The mathematical calculation performed, if any.")
    verification_status: Optional[str] = Field(default=None, description="The verification status of this claim (e.g., 'verified', 'unverified', 'failed').")
    verification_details: Optional[Dict[str, Any]] = Field(default=None, description="Structured mathematical or semantic verification output.")

class OutputGraphNode(BaseModel):
    id: str = Field(..., description="Unique identifier for the node within this graph output.")
    label: str = Field(..., description="Semantic label for the node, e.g., 'Concept', 'Metric'.")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Basic key/value properties of the node.")
    provenance: Optional[ProvenanceBundle] = Field(default=None, description="Deep provenance metadata for UI hover-cards.")

class OutputGraphEdge(BaseModel):
    source_id: str = Field(..., description="ID of the source node.")
    target_id: str = Field(..., description="ID of the target node.")
    type: str = Field(..., description="Type of the relationship, e.g., 'DERIVES_FROM'.")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Basic key/value properties of the edge.")

class OutputGraph(BaseModel):
    nodes: List[OutputGraphNode] = Field(default_factory=list)
    edges: List[OutputGraphEdge] = Field(default_factory=list)
