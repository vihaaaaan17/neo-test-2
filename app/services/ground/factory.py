import logging
from typing import Callable, Awaitable, Any, Protocol, Optional
from uuid import UUID
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.api.deps.llm import get_llm_gateway, get_embed_gateway
from app.services.hybrid_retrieval import HybridRetrievalService

logger = logging.getLogger(__name__)

def get_hybrid_retrieval_service() -> HybridRetrievalService:
    return HybridRetrievalService()

class GroundEngineProtocol(Protocol):
    async def run(self, workspace_id: UUID, query: str, **kwargs) -> dict[str, Any]:
        ...

async def get_ground_engine(
    request: Request = None,
    hybrid_retriever: HybridRetrievalService = Depends(get_hybrid_retrieval_service),
    llm_gateway: Callable[[str], Awaitable[str]] = Depends(get_llm_gateway),
    embed_gateway: Callable[[str], Awaitable[list[float]]] = Depends(get_embed_gateway)
) -> GroundEngineProtocol:
    """
    Factory dependency that returns a unified Ground Engine based on the configuration.
    """
    if settings.OPEN_NOTEBOOK_ENABLED:
        logger.info("Instantiating OpenNotebookGroundEngine")
        from app.integrations.open_notebook.ground_engine import OpenNotebookGroundEngine
        # We instantiate with an empty db since it's typically injected via dependencies 
        # or we just rely on passing db into run() for OpenNotebook
        http_client = None
        if request and hasattr(request, "app") and hasattr(request.app, "state"):
            http_client = getattr(request.app.state, "http_client", None)
        return OpenNotebookGroundEngine(http_client=http_client)
    else:
        logger.info("Instantiating legacy GroundModeOrchestrator")
        from app.orchestration.ground_mode import GroundModeOrchestrator
        return GroundModeOrchestrator(
            hybrid_retriever=hybrid_retriever,
            llm_gateway=llm_gateway,
            embed_gateway=embed_gateway
        )
