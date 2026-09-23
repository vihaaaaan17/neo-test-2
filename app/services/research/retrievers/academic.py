import logging
import httpx
import xml.etree.ElementTree as ET
from typing import List, Any
from urllib.parse import quote_plus
from app.services.research.retrievers.base import BaseRetriever, ResearchSourceResult
from app.services.research.normalization import ResearchNormalizationService
from app.services.research.budget import UsageTracker

logger = logging.getLogger(__name__)

class AcademicRetriever(BaseRetriever):
    name: str = "arxiv"

    def __init__(self):
        self.normalizer = ResearchNormalizationService()
        self.base_url = "http://export.arxiv.org/api/query"
        self.usage_tracker = UsageTracker()

    async def retrieve(self, query: str, max_results: int = 5, **kwargs: Any) -> List[ResearchSourceResult]:
        self.usage_tracker.track_search_call()
        """
        Queries the arXiv API and returns normalized ResearchSourceResult items.
        """
        encoded_query = quote_plus(query)
        url = f"{self.base_url}?search_query=all:{encoded_query}&start=0&max_results={max_results}"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                if response.status_code != 200:
                    logger.error(f"AcademicRetriever (arXiv) returned status code {response.status_code}")
                    return []

                xml_data = response.text
                return self._parse_arxiv_atom(xml_data, query)

        except Exception as e:
            self.usage_tracker.track_error(str(e))
            logger.exception(f"AcademicRetriever failed during query '{query}': {e}")
            return []

    def _parse_arxiv_atom(self, xml_data: str, query: str) -> List[ResearchSourceResult]:
        source_results = []
        try:
            root = ET.fromstring(xml_data)
            # Namespace for Atom feed
            ns = {'atom': 'http://www.w3.org/2005/Atom'}

            entries = root.findall('atom:entry', ns)
            for entry in entries:
                title_elem = entry.find('atom:title', ns)
                summary_elem = entry.find('atom:summary', ns)
                id_elem = entry.find('atom:id', ns)

                title = title_elem.text.strip().replace('\n', ' ') if title_elem is not None and title_elem.text else "Untitled"
                content = summary_elem.text.strip().replace('\n', ' ') if summary_elem is not None and summary_elem.text else ""
                url = id_elem.text.strip() if id_elem is not None and id_elem.text else ""

                normalized_url = self.normalizer.normalize_url(url)
                fingerprint = self.normalizer.generate_fingerprint(content, normalized_url)

                source_results.append(
                    ResearchSourceResult(
                        url=normalized_url,
                        title=title,
                        content=content,
                        query=query,
                        retriever=self.name,
                        provider="arxiv",
                        source_resolution_status="unresolved_external",
                        provider_reference={
                            "provider": "arxiv"
                        },
                        metadata={
                            "provider": "arxiv"
                        },
                        provenance={
                            "title": title,
                            "url": url,
                            "fingerprint": fingerprint,
                            "source_resolution_status": "unresolved_external"
                        }
                    )
                )

        except Exception as e:
            logger.error(f"Failed to parse arXiv Atom XML: {e}")

        return source_results
