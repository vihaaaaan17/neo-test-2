import asyncio
from typing import Optional, Type, Any
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

try:
    from gpt_researcher import GPTResearcher
except ImportError:
    GPTResearcher = None

class GPTResearcherInput(BaseModel):
    query: str = Field(description="The specific topic or sub-topic to research deeply across the web.")
    report_type: str = Field(default="research_report", description="The type of report to generate (e.g. research_report, subtopic_report).")

class GPTResearcherTool(BaseTool):
    name: str = "gpt_researcher_deep_crawl"
    description: str = (
        "A deep research tool that crawls the web, aggregates multiple sources, "
        "and synthesizes a comprehensive report on a given topic."
    )
    args_schema: Type[BaseModel] = GPTResearcherInput
    
    def _run(
        self,
        query: str,
        report_type: str = "research_report",
        run_manager: Optional[Any] = None,
    ) -> str:
        """Use the tool synchronously."""
        raise NotImplementedError("GPTResearcherTool only supports async execution. Use ainvoke.")

    async def _arun(
        self,
        query: str,
        report_type: str = "research_report",
        run_manager: Optional[Any] = None,
    ) -> str:
        """Use the tool asynchronously."""
        if GPTResearcher is None:
            raise ImportError("gpt_researcher is not installed. Please install it to use GPTResearcherTool.")
            
        researcher = GPTResearcher(query=query, report_type=report_type)
        # Conduct research on the given query
        await researcher.conduct_research()
        # Write the report
        report = await researcher.write_report()
        return report
