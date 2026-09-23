import logging
from typing import List, Any, Dict
from app.services.research.retrievers.base import BaseRetriever, ResearchSourceResult, ResearchRetrievalPolicy
from app.services.research.normalization import ResearchNormalizationService
from app.services.research.budget import UsageTracker

logger = logging.getLogger(__name__)

class MCPRetriever(BaseRetriever):
    name: str = "mcp"

    def __init__(self, policy: ResearchRetrievalPolicy, mcp_client_manager: Any = None):
        self.policy = policy
        self.mcp_client_manager = mcp_client_manager
        self.normalizer = ResearchNormalizationService()
        self.usage_tracker = UsageTracker()

    async def retrieve(self, query: str, max_results: int = 5, **kwargs: Any) -> List[ResearchSourceResult]:
        self.usage_tracker.track_search_call()
        """
        Executes an MCP tool call respecting workspace boundaries and allowed servers.
        """
        if not self.policy.allow_mcp:
            logger.warning("MCPRetriever: MCP retrieval attempted but disallowed by policy.")
            return []

        server_name = kwargs.get("server_name")
        tool_name = kwargs.get("tool_name")

        if not server_name or not tool_name:
            logger.error("MCPRetriever: Missing 'server_name' or 'tool_name' in kwargs.")
            return []

        # Enforce server boundary ACL
        if server_name not in self.policy.allowed_mcp_servers:
            logger.warning(f"MCPRetriever: Server '{server_name}' is not in allowed_mcp_servers policy.")
            return []

        if not self.mcp_client_manager:
            logger.error("MCPRetriever: No MCP client manager configured.")
            return []

        try:
            logger.info(f"MCPRetriever: calling MCP server '{server_name}', tool '{tool_name}' with query: '{query}'")
            # Execute through MCP client manager
            response = await self.mcp_client_manager.call_tool(
                server_name=server_name,
                tool_name=tool_name,
                arguments={"query": query, "max_results": max_results, **kwargs.get("arguments", {})}
            )

            content = str(response.get("content", ""))
            title = response.get("title", f"MCP Result from {server_name}:{tool_name}")
            url = response.get("url", f"mcp://{server_name}/{tool_name}")

            normalized_url = self.normalizer.normalize_url(url)
            fingerprint = self.normalizer.generate_fingerprint(content, normalized_url)

            return [
                ResearchSourceResult(
                    url=normalized_url,
                    title=title,
                    content=content,
                    query=query,
                    retriever=self.name,
                    provider="mcp",
                    source_resolution_status="unresolved_external",
                    provider_reference={
                        "server_name": server_name,
                        "tool_name": tool_name
                    },
                    metadata={
                        "server_name": server_name,
                        "tool_name": tool_name
                    },
                    provenance={
                        "title": title,
                        "url": url,
                        "fingerprint": fingerprint,
                        "source_resolution_status": "unresolved_external"
                    }
                )
            ]

        except Exception as e:
            self.usage_tracker.track_error(str(e))
            logger.exception(f"MCPRetriever failed for server '{server_name}', tool '{tool_name}': {e}")
            return []
