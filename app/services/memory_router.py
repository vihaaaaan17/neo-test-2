from uuid import UUID
from typing import Optional, List, Dict, Any
from arq import ArqRedis
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.knowledge import KnowledgeRepository
from app.schemas.knowledge import KnowledgeMemoryCreate
from app.models.knowledge import KnowledgeMemory
from app.services.quota import QuotaService
from app.services.memory.policy import GroundContextPolicy, ResearchContextPolicy
from app.services.chat.context import (
    build_ground_context,
    build_research_context,
    GroundContext,
    ResearchContext,
    estimate_tokens
)


class MemoryRouter:
    """
    Central memory and context router.
    Cleanly separates write routing, policy enforcement, and context assembly.
    """

    def __init__(
        self,
        repository: KnowledgeRepository,
        quota: QuotaService | None = None,
        arq_pool: ArqRedis | None = None
    ):
        self.repository = repository
        self.quota = quota
        self.arq_pool = arq_pool

    async def route_to_memory(
        self,
        owner_id: UUID,
        workspace_id: UUID,
        data: KnowledgeMemoryCreate
    ) -> KnowledgeMemory:
        """
        Intercepts memory pushes, enforcing policy boundaries before persisting.
        Ground mode execution is strictly prohibited from writing KnowledgeMemory.
        """
        # Policy enforcement: Ground mode is strictly denied KnowledgeMemory persistence
        if data.provenance and data.provenance.source_mode == "ground":
            raise ValueError(
                "Ground mode is strictly prohibited from writing KnowledgeMemory per GroundContextPolicy"
            )

        if self.quota:
            await self.quota.check_knowledge_limit(workspace_id)

        memory = await self.repository.create_knowledge(
            owner_id=owner_id,
            workspace_id=workspace_id,
            data=data
        )

        if self.arq_pool:
            await self.arq_pool.enqueue_job("sync_knowledge_to_graph_job", knowledge_id=str(memory.knowledge_id))

        return memory

    async def assemble_ground_context(
        self,
        session: AsyncSession,
        workspace_id: UUID,
        conversation_id: UUID,
        query: str,
        explicit_scope: Optional[List[UUID]] = None,
        max_history_turns: int = 5
    ) -> GroundContext:
        """
        Routes Ground context assembly through policy-governed GroundContextPolicy.
        """
        return await build_ground_context(
            session=session,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            query=query,
            explicit_scope=explicit_scope,
            max_history_turns=max_history_turns
        )

    async def assemble_research_context(
        self,
        session: AsyncSession,
        workspace_id: UUID,
        conversation_id: UUID,
        query: str,
        token_budget: int = 8000,
        working_memory: Optional[Dict[str, Any]] = None,
        output_graph: Optional[Dict[str, Any]] = None,
        max_history_turns: int = 20
    ) -> ResearchContext:
        """
        Routes Research context assembly through deterministic reverse-priority eviction.
        """
        return await build_research_context(
            session=session,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            query=query,
            token_budget=token_budget,
            working_memory=working_memory,
            output_graph=output_graph,
            max_history_turns=max_history_turns
        )


class MemoryRouterService:
    """
    Lightweight heuristic context builder for MemoryItem bundles.
    Preserved for backward compatibility with orchestrators and tests.
    """

    @staticmethod
    def estimate_tokens(text: str) -> int:
        return estimate_tokens(text)

    @staticmethod
    def build_context(items: list['MemoryItem'], token_budget: int) -> 'ContextBundle':
        from app.schemas.context import ContextBundle

        # Priority mapping: lower number means it is evicted FIRST
        priority_map = {
            "episodic": 1,
            "knowledge": 2,
            "source": 3,
            "working": 4
        }

        # Calculate initial tokens
        for item in items:
            item._estimated_tokens = MemoryRouterService.estimate_tokens(item.text)

        total_tokens = sum(getattr(item, "_estimated_tokens", 0) for item in items)

        if total_tokens <= token_budget:
            return ContextBundle(budget=token_budget, total_tokens=total_tokens, items=items, evicted_items=[])

        # We need to evict items. Sort items by priority (lowest priority first to drop).
        sorted_items = sorted(items, key=lambda x: (priority_map.get(x.type, 0), x.id))

        evicted = []
        kept = []

        # We process from lowest priority (Episodic) to highest priority (Working)
        for item in sorted_items:
            if total_tokens > token_budget and item.type != "working":
                # We can evict this item
                total_tokens -= getattr(item, "_estimated_tokens", 0)
                evicted.append(item)
            else:
                # Keep it
                kept.append(item)

        # Return the bundle with kept items in their original relative order
        kept_ids = {item.id for item in kept}
        final_items = [item for item in items if item.id in kept_ids]

        return ContextBundle(budget=token_budget, total_tokens=total_tokens, items=final_items, evicted_items=evicted)
