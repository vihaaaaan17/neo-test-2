from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.source import Source, SourceSnapshot
from app.models.block import DocumentBlock
from app.models.research import ResearchRun, ResearchEvidence, ResearchArtifact
from app.models.knowledge import KnowledgeMemory
from app.models.conversation import ConversationTurn
from app.schemas.graph import ProvenanceRef, ProvenanceBundle
from app.services.research.verification import verify_claim, VerificationResult


class CrossWorkspaceBoundaryError(Exception):
    """Raised when a provenance reference points across workspace boundaries or does not exist."""
    pass


class DerivationService:
    """
    Normalizes candidate outputs and enforces fail-closed multi-tenant provenance lineage.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    def build_provenance_bundle(
        self,
        refs: List[ProvenanceRef],
        calculation: Optional[str] = None,
        verification_result: Optional[VerificationResult] = None,
    ) -> ProvenanceBundle:
        """
        Builds a typed ProvenanceBundle from a list of ProvenanceRef items and optional verification details.
        """
        status = verification_result.status if verification_result else None
        details = verification_result.reason if verification_result else None

        return ProvenanceBundle(
            derived_from=refs,
            derived_from_refs=[ref.ref_id for ref in refs],
            calculation=calculation,
            verification_status=status,
            verification_details=details,
        )

    async def validate_provenance_lineage(
        self,
        workspace_id: UUID,
        refs: List[ProvenanceRef],
    ) -> bool:
        """
        Strictly validates that every reference in the provenance bundle exists and belongs to the given workspace.
        Fails closed by raising CrossWorkspaceBoundaryError if any reference is missing or from another workspace.
        """
        if not refs:
            return True

        for ref in refs:
            ref_type = ref.ref_type
            ref_id = ref.ref_id

            if ref_type == "source":
                stmt = select(Source.source_id).where(
                    Source.source_id == ref_id,
                    Source.workspace_id == workspace_id,
                )
                res = await self.session.execute(stmt)
                if not res.scalar_one_or_none():
                    raise CrossWorkspaceBoundaryError(
                        f"Provenance reference 'source:{ref_id}' is invalid or does not belong to workspace {workspace_id}."
                    )

            elif ref_type == "source_snapshot":
                stmt = (
                    select(SourceSnapshot.snapshot_id)
                    .join(Source, SourceSnapshot.source_id == Source.source_id)
                    .where(
                        SourceSnapshot.snapshot_id == ref_id,
                        Source.workspace_id == workspace_id,
                    )
                )
                res = await self.session.execute(stmt)
                if not res.scalar_one_or_none():
                    raise CrossWorkspaceBoundaryError(
                        f"Provenance reference 'source_snapshot:{ref_id}' is invalid or does not belong to workspace {workspace_id}."
                    )

            elif ref_type == "block":
                stmt = (
                    select(DocumentBlock.block_id)
                    .join(Source, DocumentBlock.source_id == Source.source_id)
                    .where(
                        DocumentBlock.block_id == ref_id,
                        Source.workspace_id == workspace_id,
                    )
                )
                res = await self.session.execute(stmt)
                if not res.scalar_one_or_none():
                    raise CrossWorkspaceBoundaryError(
                        f"Provenance reference 'block:{ref_id}' is invalid or does not belong to workspace {workspace_id}."
                    )

            elif ref_type == "research_evidence":
                stmt = (
                    select(ResearchEvidence.evidence_id)
                    .join(ResearchRun, ResearchEvidence.run_id == ResearchRun.run_id)
                    .where(
                        ResearchEvidence.evidence_id == ref_id,
                        ResearchRun.workspace_id == workspace_id,
                    )
                )
                res = await self.session.execute(stmt)
                if not res.scalar_one_or_none():
                    raise CrossWorkspaceBoundaryError(
                        f"Provenance reference 'research_evidence:{ref_id}' is invalid or does not belong to workspace {workspace_id}."
                    )

            elif ref_type == "research_artifact":
                stmt = (
                    select(ResearchArtifact.artifact_id)
                    .join(ResearchRun, ResearchArtifact.run_id == ResearchRun.run_id)
                    .where(
                        ResearchArtifact.artifact_id == ref_id,
                        ResearchRun.workspace_id == workspace_id,
                    )
                )
                res = await self.session.execute(stmt)
                if not res.scalar_one_or_none():
                    raise CrossWorkspaceBoundaryError(
                        f"Provenance reference 'research_artifact:{ref_id}' is invalid or does not belong to workspace {workspace_id}."
                    )

            elif ref_type == "knowledge_memory":
                stmt = select(KnowledgeMemory.knowledge_id).where(
                    KnowledgeMemory.knowledge_id == ref_id,
                    KnowledgeMemory.workspace_id == workspace_id,
                )
                res = await self.session.execute(stmt)
                if not res.scalar_one_or_none():
                    raise CrossWorkspaceBoundaryError(
                        f"Provenance reference 'knowledge_memory:{ref_id}' is invalid or does not belong to workspace {workspace_id}."
                    )

            elif ref_type == "conversation_turn":
                stmt = select(ConversationTurn.turn_id).where(
                    ConversationTurn.turn_id == ref_id,
                    ConversationTurn.workspace_id == workspace_id,
                )
                res = await self.session.execute(stmt)
                if not res.scalar_one_or_none():
                    raise CrossWorkspaceBoundaryError(
                        f"Provenance reference 'conversation_turn:{ref_id}' is invalid or does not belong to workspace {workspace_id}."
                    )

            else:
                raise CrossWorkspaceBoundaryError(f"Unsupported provenance reference type: '{ref_type}'.")

        return True

    async def normalize_derivation(
        self,
        workspace_id: UUID,
        candidate_dict: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Validates provenance references, runs deterministic verification if derivations are present,
        and returns a normalized candidate payload dictionary.
        """
        payload = candidate_dict.get("payload") or {}

        # 1. Validate provenance references if explicitly provided
        prov_dict = payload.get("provenance") or {}
        derived_from_raw = prov_dict.get("derived_from") or []
        refs = []
        for item in derived_from_raw:
            if isinstance(item, dict):
                refs.append(ProvenanceRef(**item))
            elif isinstance(item, ProvenanceRef):
                refs.append(item)

        # Also collect any top-level evidence_refs
        evidence_refs_raw = payload.get("evidence_refs") or []
        for ev_id in evidence_refs_raw:
            ev_uuid = UUID(str(ev_id))
            refs.append(ProvenanceRef(ref_type="research_evidence", ref_id=ev_uuid))

        if refs:
            await self.validate_provenance_lineage(workspace_id, refs)

        # 2. Run deterministic calculation verification if derivation present
        verification_result = None
        if "derivation" in payload:
            verification_result = verify_claim(payload)
            candidate_dict["verification_status"] = verification_result.status
            candidate_dict["verification_reason"] = verification_result.reason
            candidate_dict["verification_metadata"] = verification_result.metadata
        elif candidate_dict.get("verification_status") is None:
            candidate_dict["verification_status"] = "unverified"
            candidate_dict["verification_reason"] = {"detail": "No mathematical derivation to verify"}

        # 3. Synchronize ProvenanceBundle in payload if refs or derivation exist
        if refs or verification_result:
            calc_expr = payload.get("derivation", {}).get("expression") if isinstance(payload.get("derivation"), dict) else None
            bundle = self.build_provenance_bundle(refs, calculation=calc_expr, verification_result=verification_result)
            payload["provenance"] = bundle.model_dump()
            candidate_dict["payload"] = payload

        return candidate_dict
