import logging
from typing import Dict, List, Optional, Any
from app.services.research.retrievers.base import BaseRetriever, ResearchSourceResult, ResearchRetrievalPolicy

logger = logging.getLogger(__name__)

class RetrieverRegistry:
    """
    Central registry for managing and invoking retrievers (web, academic, mcp, etc.)
    subject to ResearchRetrievalPolicy constraints.
    """

    def __init__(self, policy: Optional[ResearchRetrievalPolicy] = None):
        self.policy = policy or ResearchRetrievalPolicy()
        self._retrievers: Dict[str, BaseRetriever] = {}
        self._call_count = 0

    def register(self, name: str, retriever: BaseRetriever) -> None:
        """Register a retriever instance under a name."""
        self._retrievers[name] = retriever
        logger.info(f"RetrieverRegistry: registered retriever '{name}'")

    def get(self, name: str) -> Optional[BaseRetriever]:
        """Get a registered retriever by name."""
        return self._retrievers.get(name)

    def list_retrievers(self) -> List[str]:
        """List all registered retriever names."""
        return list(self._retrievers.keys())

    async def retrieve(
        self,
        query: str,
        retriever_name: Optional[str] = None,
        max_results: int = 5,
        **kwargs: Any
    ) -> List[ResearchSourceResult]:
        """
        Execute retrieval using the specified retriever or policy defaults,
        enforcing call budgets and policy permissions.
        """
        # 1. Enforce call budget
        if self.policy.max_calls is not None and self._call_count >= self.policy.max_calls:
            logger.warning(f"RetrieverRegistry: Max retrieval calls ({self.policy.max_calls}) exceeded.")
            return []

        # 2. Determine which retriever to use
        target_name = retriever_name
        if not target_name:
            # Default to preferred web provider
            target_name = self.policy.preferred_web_provider

        retriever = self.get(target_name)
        if not retriever:
            # Try fallback web provider if target was web
            if target_name == self.policy.preferred_web_provider and self.policy.fallback_web_provider:
                target_name = self.policy.fallback_web_provider
                retriever = self.get(target_name)

        if not retriever:
            raise ValueError(f"Retriever '{target_name}' is not registered or available.")

        # 3. Policy checks
        if target_name in ("tavily", "web") and not self.policy.allow_web:
            logger.warning(f"RetrieverRegistry: Web retrieval requested but disallowed by policy.")
            return []
        if target_name in ("arxiv", "academic") and not self.policy.allow_academic:
            logger.warning(f"RetrieverRegistry: Academic retrieval requested but disallowed by policy.")
            return []
        if target_name == "mcp" and not self.policy.allow_mcp:
            logger.warning(f"RetrieverRegistry: MCP retrieval requested but disallowed by policy.")
            return []

        # 4. Execute retrieval
        self._call_count += 1
        logger.info(f"RetrieverRegistry: executing retrieval with '{target_name}' for query: '{query}'")
        results = await retriever.retrieve(query=query, max_results=max_results, **kwargs)
        return results
