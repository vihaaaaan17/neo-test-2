import logging
import os
from typing import List, Any, Optional
try:
    from tavily import AsyncTavilyClient
except ImportError:
    AsyncTavilyClient = None  # type: ignore[assignment,misc]
from app.services.research.retrievers.base import BaseRetriever, ResearchSourceResult
from app.services.research.normalization import ResearchNormalizationService
from app.services.research.budget import UsageTracker

logger = logging.getLogger(__name__)

class WebRetriever(BaseRetriever):
    name: str = "tavily"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("TAVILY_API_KEY")
        if not self.api_key:
            logger.warning("WebRetriever: TAVILY_API_KEY is not set.")
            self.client = None
        else:
            self.client = AsyncTavilyClient(api_key=self.api_key)
        self.normalizer = ResearchNormalizationService()
        self.usage_tracker = UsageTracker()

    async def retrieve(self, query: str, max_results: int = 5, **kwargs: Any) -> List[ResearchSourceResult]:
        # Initialize usage tracking
        self.usage_tracker.track_search_call()
        if not self.client:
            logger.error("WebRetriever: Tavily client not initialized (missing API key).")
            return []

        try:
            topic = kwargs.get("topic", "general")
            response = await self.client.search(
                query=query,
                search_depth="advanced",
                max_results=max_results,
                include_raw_content=True,
                topic=topic
            )

            results = response.get("results", [])
            source_results = []

            for res in results:
                url = res.get("url", "")
                title = res.get("title", "Untitled")
                content = res.get("raw_content", "") or res.get("content", "")

                # Normalize URL and generate fingerprint
                normalized_url = self.normalizer.normalize_url(url)
                fingerprint = self.normalizer.generate_fingerprint(content, normalized_url)

                source_results.append(
                    ResearchSourceResult(
                        url=normalized_url,
                        title=title,
                        content=content,
                        query=query,
                        retriever=self.name,
                        provider="tavily",
                        source_resolution_status="unresolved_external",
                        provider_reference={
                            "raw_score": res.get("score"),
                            "topic": topic
                        },
                        metadata={
                            "raw_score": res.get("score"),
                            "topic": topic
                        },
                        provenance={
                            "title": title,
                            "url": url,
                            "fingerprint": fingerprint,
                            "source_resolution_status": "unresolved_external"
                        }
                    )
                )

            return source_results

        except Exception as e:
            self.usage_tracker.track_error(str(e))
            logger.exception(f"WebRetriever failed during search for query '{query}': {e}")
            return []
