from typing import Optional, Type, Any
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from langchain_core.runnables import RunnableConfig
from app.services.research.retrievers.gpt_researcher import GPTResearcherRetriever
from app.services.research.normalization import ResearchNormalizationService
from app.core.database import async_session_maker
from app.repositories.research import ResearchRepository
from uuid import UUID

class GPTResearcherInput(BaseModel):
    query: str = Field(description="The specific topic or sub-topic to research deeply across the web.")
    report_type: str = Field(default="research_report", description="The type of report to generate (e.g. research_report, subtopic_report).")

class GPTResearcherTool(BaseTool):
    name: str = "gpt_researcher_deep_crawl"
    description: str = (
        "A deep research tool that crawls the web, aggregates multiple sources, "
        "and returns normalized ResearchSourceResult items (provenance-tracked evidence)."
    )
    args_schema: Type[BaseModel] = GPTResearcherInput

    # We inject the retriever instance here
    retriever: Optional[GPTResearcherRetriever] = Field(default_factory=GPTResearcherRetriever)

    def _run(self, *args, **kwargs):
        raise NotImplementedError("GPTResearcherTool only supports async execution.")

    async def _arun(
        self,
        query: str,
        report_type: str = "research_report",
        run_manager: Optional[Any] = None,
        config: RunnableConfig = None
    ) -> str:
        """Use the tool asynchronously."""
        config = config or {}
        metadata = config.get("metadata", {})
        run_id = UUID(metadata.get("run_id"))
        workspace_id = UUID(metadata.get("owner"))

        # Retrieve structured results using the GPTResearcherRetriever
        results = await self.retriever.retrieve(query=query, report_type=report_type)

        # Persist results as evidence in Neosis DB
        async with async_session_maker() as session:
            repo = ResearchRepository(session)

            # Verify workspace boundary
            await repo._verify_run_workspace(run_id, workspace_id)

            for result in results:
                try:
                    await repo.create_evidence(
                        workspace_id=workspace_id,
                        run_id=run_id,
                        task_id=None,
                        source_id=None,
                        retriever=result.retriever,
                        query=result.query,
                        content=result.content,
                        locator=result.url,
                        fingerprint=result.provenance.get("fingerprint"),
                        tags=["gpt_researcher_result"],
                        provenance=result.provenance,
                        source_resolution_status=result.source_resolution_status,
                        provider=result.provider,
                        provider_reference=result.provider_reference
                    )
                except Exception as e:
                    # Log but continue for other evidence
                    import logging
                    logging.getLogger(__name__).error(f"Failed to persist evidence for {result.url}: {e}")

        # Return formatted output for the LLM
        formatted_output = f"GPT Researcher successfully retrieved {len(results)} sources and persisted them to evidence.\n\n"
        for i, res in enumerate(results):
            formatted_output += f"{i+1}. {res.title} ({res.url})\n"

        return formatted_output
