import logging
import os
from typing import List, Any, Optional, Callable, Awaitable, Dict
from app.services.research.retrievers.base import BaseRetriever, ResearchSourceResult
from app.services.research.normalization import ResearchNormalizationService
from app.services.research.budget import UsageTracker

logger = logging.getLogger(__name__)

try:
    from gpt_researcher import GPTResearcher
    from gpt_researcher.utils.enum import ReportSource
except ImportError:
    GPTResearcher = None
    ReportSource = None
    logger.warning("GPTResearcher or its dependencies not found. GPTResearcherRetriever will be unavailable.")

class GPTResearcherRetriever(BaseRetriever):
    name: str = "gpt_researcher"

    def __init__(
        self,
        llm_gateway: Optional[Callable[[str, str, str], Awaitable[str]]] = None, # prompt, model, provider
        normalization_service: Optional[ResearchNormalizationService] = None,
    ):
        if GPTResearcher is None:
            raise ImportError("GPTResearcher is not installed. Cannot initialize GPTResearcherRetriever.")

        self.llm_gateway = llm_gateway
        self.normalizer = normalization_service or ResearchNormalizationService()
        self.usage_tracker = UsageTracker()

    async def retrieve(self, query: str, max_results: int = 5, **kwargs: Any) -> List[ResearchSourceResult]:
        self.usage_tracker.track_search_call()
        if GPTResearcher is None:
            logger.error("GPTResearcherRetriever: GPTResearcher not available.")
            return []

        report_type = kwargs.get("report_type", "research_report")
        report_source = kwargs.get("report_source", ReportSource.Web.value if ReportSource else "web")
        source_urls = kwargs.get("source_urls", [])
        query_domains = kwargs.get("query_domains", [])

        try:
            # GPTResearcher expects an LLM_MODEL in env, but we pass via gateway
            # Temporarily set to avoid internal error, reset after
            # This is a hack due to GPTResearcher's tight coupling with os.environ
            original_llm_model = os.environ.get("LLM_MODEL")
            os.environ["LLM_MODEL"] = kwargs.get("llm_model", "gpt-4o-mini") # Default to a small model

            researcher = GPTResearcher(
                query=query,
                report_type=report_type,
                report_source=report_source,
                source_urls=source_urls,
                query_domains=query_domains,
                llm_provider=self._get_gpt_researcher_llm_provider(kwargs.get("llm_provider", "openai"), **kwargs)
            )

            # Conduct research - this will internally use its own tools/retrievers
            await researcher.conduct_research()

            # Extract results (sources are what we care about for evidence)
            raw_sources = researcher.get_results()

            research_source_results = []
            for source in raw_sources:
                url = source.get("link", "")
                title = source.get("title", "Untitled")
                content = source.get("content", "")

                normalized_url = self.normalizer.normalize_url(url)
                fingerprint = self.normalizer.generate_fingerprint(content, normalized_url)

                research_source_results.append(
                    ResearchSourceResult(
                        url=normalized_url,
                        title=title,
                        content=content,
                        query=query,
                        retriever=self.name,
                        metadata={
                            "report_type": report_type,
                            "report_source": report_source,
                            "raw_score": source.get("score"),
                        },
                        provenance={
                            "title": title,
                            "url": url,
                            "fingerprint": fingerprint,
                            "source_resolution_status": "unresolved_external"
                        }
                    )
                )

            return research_source_results

        except Exception as e:
            self.usage_tracker.track_error(str(e))
            logger.exception(f"GPTResearcherRetriever failed for query '{query}': {e}")
            return []
        finally:
            # Restore original LLM_MODEL env var
            if original_llm_model is not None:
                os.environ["LLM_MODEL"] = original_llm_model
            else:
                del os.environ["LLM_MODEL"]

    def _get_gpt_researcher_llm_provider(self, provider_name: str, **kwargs: Any) -> Any:
        """
        Creates a mock LLM provider for GPTResearcher that uses Neosis's llm_gateway.
        This is necessary because GPTResearcher expects to manage its own LLM.
        """
        from gpt_researcher.llm_provider import GenericLLMProvider
        from gpt_researcher.config import Config

        # Patching GenericLLMProvider to use our llm_gateway
        class PatchedLLMProvider(GenericLLMProvider):
            def __init__(self, model: str, provider: str, llm_gateway: Callable[[str, str, str], Awaitable[str]], **kwargs):
                # config needs to be a Config object, but for mocking purposes, we can pass minimal
                config_instance = Config()
                config_instance.llm_model = model
                config_instance.llm_provider = provider
                super().__init__(model, provider, config_instance, **kwargs)
                self._llm_gateway = llm_gateway

            async def get_chat_response(self, prompt: str, *args, **kwargs) -> str:
                return await self._llm_gateway(prompt, self.model, self.provider)

            # We need to override the method that sets the client to prevent GPTResearcher
            # from trying to instantiate its own client if that is problematic. For now, we assume
            # get_chat_response is the primary interaction point.
            def _set_llm_client(self):
                self.model = os.environ.get("LLM_MODEL", self.model)
                # In a real scenario, we might need a more sophisticated mock or integration
                # For now, we bypass the internal client setup as get_chat_response uses our gateway

        return PatchedLLMProvider(
            model=kwargs.get("llm_model", "gpt-4o-mini"),
            provider=provider_name,
            llm_gateway=self.llm_gateway
        )

