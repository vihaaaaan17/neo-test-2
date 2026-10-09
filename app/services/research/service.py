import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.research import ResearchRun, ResearchArtifact
from app.repositories.research import ResearchRepository
from app.services.memory_router import MemoryRouter
from app.repositories.graph import GraphRepository
from app.schemas.knowledge import KnowledgeMemoryCreate, Provenance
from app.schemas.graph import OutputGraph, OutputGraphNode, OutputGraphEdge, ProvenanceBundle

class ResearchService:
    """
    Central coordinator for Research Engine Phase 2.
    Implements explicit promotion boundaries.
    """

    def __init__(
        self,
        research_repo: ResearchRepository,
        memory_router: Optional[MemoryRouter] = None,
        graph_repo: Optional[GraphRepository] = None
    ):
        self.research_repo = research_repo
        self.memory_router = memory_router
        self.graph_repo = graph_repo

    async def finalize_report(
        self,
        workspace_id: uuid.UUID,
        run_id: uuid.UUID,
        objective: str,
        report: str,
    ) -> ResearchArtifact:
        """
        Engine-agnostic finalization of a completed run's final report.

        Persists the canonical ResearchReport and emits a `memory_candidate` artifact in `pending_review`
        with v2 provenance (evidence refs + the originating conversation turn). Candidates are NEVER
        auto-promoted: human review gates every transition to KnowledgeMemory / Output KG.
        """
        repo = self.research_repo
        await repo.create_report(
            workspace_id=workspace_id,
            run_id=run_id,
            objective=objective,
            content=report,
        )

        evidence_list = await repo.list_evidence_for_run(workspace_id, run_id) or []
        evidence_refs = [str(ev.evidence_id) for ev in evidence_list]
        source_refs = [{"ref_type": "research_evidence", "ref_id": ref} for ref in evidence_refs]

        run = await repo.get_run(workspace_id, run_id)
        if run and run.turn_id:
            source_refs.append({"ref_type": "conversation_turn", "ref_id": str(run.turn_id)})

        payload = {
            "candidate_type": "memory_candidate",
            "content": report,
            "text": report,
            "evidence_refs": evidence_refs,
            "source_refs": source_refs,
            "provenance": {
                "source_refs": evidence_refs,
                "derived_from_refs": evidence_refs,
                "derived_from": source_refs,
            },
            "proposed_memory_type": "research_memory",
            "provenance_version": "v2",
            "domain": "deep_research",
            "metadata": {"source": run.engine if run else "unknown", "objective": objective},
        }
        return await repo.create_artifact(
            workspace_id=workspace_id,
            run_id=run_id,
            artifact_type="memory_candidate",
            payload=payload,
            promotion_status="pending_review",
        )

    async def promote_memory_candidates(self, workspace_id: uuid.UUID, run_id: uuid.UUID, owner_id: uuid.UUID) -> int:
        """
        Finds all ResearchArtifacts for a given run with type='memory_candidate'
        and promotes them to the KnowledgeMemory using the MemoryRouter.
        Returns the number of memories promoted.
        """
        # Ensure run exists and belongs to workspace
        await self.research_repo._verify_run_workspace(run_id, workspace_id)
        
        stmt = (
            select(ResearchArtifact)
            .where(ResearchArtifact.run_id == run_id)
            .where(ResearchArtifact.type == "memory_candidate")
        )
        result = await self.research_repo.session.execute(stmt)
        candidates = result.scalars().all()
        
        promoted_count = 0
        for artifact in candidates:
            # We assume artifact.payload holds the memory text or payload
            content_str = artifact.payload.get("text", "") if isinstance(artifact.payload, dict) else str(artifact.payload)
            
            domain_val = artifact.payload.get("domain", "deep_research") if isinstance(artifact.payload, dict) else "deep_research"
            
            # Map artifact fields to KnowledgeMemoryCreate
            # According to schema, source_mode should be 'research' for research outputs.
            memory_data = KnowledgeMemoryCreate(
                knowledge_type="research_memory",
                content=content_str,
                domain=domain_val,
                status="active",
                provenance=Provenance(
                    source_mode="research",
                    source_refs=[]
                )
            )
            
            await self.memory_router.route_to_memory(
                owner_id=owner_id,
                workspace_id=workspace_id,
                data=memory_data
            )
            promoted_count += 1
            
        return promoted_count

    async def promote_graph_candidates(self, workspace_id: uuid.UUID, run_id: uuid.UUID) -> int:
        """
        Finds all ResearchArtifacts for a given run with type='graph_candidate'
        and promotes them via GraphRepository.project_output_graph.
        Returns the number of artifacts processed.
        """
        await self.research_repo._verify_run_workspace(run_id, workspace_id)
        
        stmt = (
            select(ResearchArtifact)
            .where(ResearchArtifact.run_id == run_id)
            .where(ResearchArtifact.type == "graph_candidate")
        )
        result = await self.research_repo.session.execute(stmt)
        candidates = result.scalars().all()
        
        promoted_count = 0
        for artifact in candidates:
            payload = artifact.payload or {}
            
            # We expect the payload dict to represent an OutputGraph structure.
            nodes_data = payload.get("nodes", [])
            edges_data = payload.get("edges", [])
            
            nodes = []
            for n in nodes_data:
                prov_data = n.get("provenance")
                provenance = None
                if prov_data:
                    provenance = ProvenanceBundle(
                        derived_from_refs=[uuid.UUID(ref) for ref in prov_data.get("derived_from_refs", [])],
                        calculation=prov_data.get("calculation"),
                        verification_status=prov_data.get("verification_status")
                    )
                nodes.append(OutputGraphNode(
                    id=n["id"],
                    label=n["label"],
                    properties=n.get("properties", {}),
                    provenance=provenance
                ))
                
            edges = []
            for e in edges_data:
                edges.append(OutputGraphEdge(
                    source_id=e["source_id"],
                    target_id=e["target_id"],
                    type=e["type"],
                    properties=e.get("properties", {})
                ))
                
            graph = OutputGraph(nodes=nodes, edges=edges)
            await self.graph_repo.project_output_graph(workspace_id=workspace_id, graph=graph)
            promoted_count += 1
            
        return promoted_count
