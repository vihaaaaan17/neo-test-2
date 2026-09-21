import asyncio
import logging
from typing import Annotated, List, Literal, Any, Optional
from uuid import UUID

from langchain_core.tools import tool, InjectedToolArg
from langchain_core.runnables import RunnableConfig
from tavily import AsyncTavilyClient
import os

from app.core.database import async_session_maker
from app.repositories.research import ResearchRepository
from app.services.research.normalization import ResearchNormalizationService

logger = logging.getLogger(__name__)

@tool(description="A search engine optimized for comprehensive, accurate, and trusted results. Useful for when you need to answer questions about current events.")
async def neosis_web_search(
    queries: List[str],
    max_results: Annotated[int, InjectedToolArg] = 5,
    topic: Annotated[Literal["general", "news", "finance"], InjectedToolArg] = "general",
    config: RunnableConfig = None
) -> str:
    """Fetch search results, immediately persist them to Neosis DB, and return formatted results.

    Args:
        queries: List of search queries to execute
        max_results: Maximum number of results to return per query
        topic: Topic filter for search results
        config: Runtime configuration (must contain run_id and workspace_id in metadata)

    Returns:
        Formatted string containing search results
    """
    tracker = config.get("configurable", {}).get("usage_tracker")
    if tracker:
        tracker.add_search_call()
        
    metadata = config.get("metadata", {})
    run_id_str = metadata.get("run_id")
    workspace_id_str = metadata.get("owner")
    
    if not run_id_str or not workspace_id_str:
        logger.warning("Neosis Web Search called without run_id or workspace_id in config metadata.")
        return "Error: Missing execution context (run_id/workspace_id)."
        
    run_id = UUID(run_id_str)
    workspace_id = UUID(workspace_id_str)
    
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return "Error: TAVILY_API_KEY is not configured."
        
    client = AsyncTavilyClient(api_key=api_key)
    
    # Execute all queries in parallel
    search_tasks = [
        client.search(
            query,
            max_results=max_results,
            include_raw_content=True,
            topic=topic
        )
        for query in queries
    ]
    
    try:
        search_results = await asyncio.gather(*search_tasks)
    except Exception as e:
        logger.exception(f"Search failed for queries {queries}: {e}")
        return f"Error executing search: {str(e)}"
        
    unique_results = {}
    for i, response in enumerate(search_results):
        query = queries[i]
        for result in response.get('results', []):
            url = result['url']
            if url not in unique_results:
                unique_results[url] = {**result, "query": query}
                
    if not unique_results:
        return "No search results found."
        
    formatted_output = "Search results: \n\n"
    
    # Save evidence to DB
    async with async_session_maker() as session:
        repo = ResearchRepository(session)
        normalizer = ResearchNormalizationService()
        
        for idx, (url, result) in enumerate(unique_results.items()):
            title = result.get('title', 'Untitled')
            raw_content = result.get('raw_content', '') or result.get('content', '')
            query = result.get('query', '')
            
            # Persist to database
            fingerprint = normalizer.normalize_evidence(
                content=raw_content,
                locator=url,
                retriever="tavily_web_search",
                query=query
            )
            
            try:
                # We enforce workspace boundary check here implicitly if the run_id is verified
                # But since create_evidence doesn't strictly verify workspace against run_id in the same call 
                # (it does it inside _verify_run_workspace if we want, but create_evidence might not do it implicitly)
                # Let's verify it first
                await repo._verify_run_workspace(run_id, workspace_id)
                
                await repo.create_evidence(
                    run_id=run_id,
                    task_id=None,
                    source_id=None, # Will be resolved later by ProvenanceService if needed
                    retriever="tavily_web_search",
                    query=query,
                    content=raw_content,
                    locator=url,
                    fingerprint=fingerprint,
                    tags=["search_result"],
                    provenance={"title": title, "url": url}
                )
            except Exception as e:
                logger.error(f"Failed to persist evidence for {url}: {e}")
            
            # Format output for the upstream agent
            formatted_output += f"\n\n--- SOURCE {idx+1}: {title} ---\n"
            formatted_output += f"URL: {url}\n\n"
            formatted_output += f"CONTENT:\n{result.get('content', '')}\n\n"
            formatted_output += "\n\n" + "-" * 80 + "\n"
            
    return formatted_output
