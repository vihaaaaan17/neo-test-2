import os
import logging
from typing import List, Dict, Any
try:
    from tavily import AsyncTavilyClient
except ImportError:
    AsyncTavilyClient = None  # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)

class WebSearchTool:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("TAVILY_API_KEY")
        if not self.api_key:
            logger.warning("TAVILY_API_KEY is not set. WebSearchTool might fail if called.")
            self.client = None
        else:
            self.client = AsyncTavilyClient(api_key=self.api_key)
            
    async def search(self, query: str, max_results: int = 5) -> str:
        """
        Executes a search query and returns the results formatted as markdown.
        """
        if not self.client:
            return "Error: Tavily API key is missing. Cannot perform web search."
            
        try:
            logger.info(f"Executing web search for: '{query}'")
            response = await self.client.search(
                query=query,
                search_depth="advanced",
                max_results=max_results,
                include_raw_content=False
            )
            
            results = response.get("results", [])
            if not results:
                return f"No results found for query: '{query}'"
                
            formatted_chunks = []
            formatted_chunks.append(f"### Web Search Results for: {query}")
            for idx, res in enumerate(results, 1):
                title = res.get("title", "Untitled")
                url = res.get("url", "")
                content = res.get("content", "")
                formatted_chunks.append(f"**[{idx}] {title}**\nURL: {url}\n{content}\n")
                
            return "\n".join(formatted_chunks)
            
        except Exception as e:
            logger.exception(f"WebSearchTool encountered an error during search: {e}")
            return f"Error executing web search: {str(e)}"
