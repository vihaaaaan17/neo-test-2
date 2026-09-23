from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

@dataclass
class ResearchSourceResult:
    url: str
    title: Optional[str]
    content: str
    query: str
    retriever: str
    provider: Optional[str] = None
    source_resolution_status: str = "unresolved_external"
    provider_reference: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    provenance: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ResearchRetrievalPolicy:
    allow_web: bool = True
    allow_academic: bool = True
    allow_mcp: bool = False
    preferred_web_provider: str = "tavily"
    fallback_web_provider: Optional[str] = None
    max_calls: Optional[int] = None
    allowed_mcp_servers: List[str] = field(default_factory=list)

class BaseRetriever(ABC):
    name: str = "base"

    @abstractmethod
    async def retrieve(self, query: str, max_results: int = 5, **kwargs) -> List[ResearchSourceResult]:
        """
        Execute retrieval for a given query and return normalized ResearchSourceResult items.
        """
        pass
