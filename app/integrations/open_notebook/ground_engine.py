import logging
import asyncio
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from app.integrations.open_notebook.client import OpenNotebookClient
from app.integrations.open_notebook.citation_mapper import map_citations
from app.models.open_notebook_binding import OpenNotebookWorkspaceBinding

logger = logging.getLogger(__name__)

class OpenNotebookGroundEngine:
    """
    Facade for interacting with Open Notebook's retrieval and asking APIs.
    """
    
    def __init__(self, workspace_id: UUID = None, http_client = None):
        self.client = OpenNotebookClient(workspace_id=str(workspace_id) if workspace_id else None, http_client=http_client)
        self.default_strategy_model = "gpt-4o-mini"
        self.default_answer_model = "gpt-4o"
        self.default_final_answer_model = "gpt-4o"
        
    async def run(self, workspace_id: UUID, query: str, db: AsyncSession) -> dict:
        logger.info(f"Running OpenNotebookGroundEngine for query: {query}")
        
        # 1. Validate the workspace has a notebook binding
        stmt = select(OpenNotebookWorkspaceBinding).where(
            OpenNotebookWorkspaceBinding.workspace_id == workspace_id,
            OpenNotebookWorkspaceBinding.status == "ACTIVE"
        )
        result = await db.execute(stmt)
        binding = result.scalars().first()
        
        if not binding:
            raise HTTPException(
                status_code=400, 
                detail="Workspace does not have an active Open Notebook binding."
            )
            
        try:
            # 2. Get default models for ask operations
            default_models = await self.client.get_default_models()
            
            # 3. Call search and ask endpoints concurrently
            search_task = self.client.search(query=query)
            ask_task = self.client.ask_simple(
                question=query,
                strategy_model=default_models.get("default_chat_model", ""),
                answer_model=default_models.get("default_chat_model", ""),
                final_answer_model=default_models.get("default_chat_model", "")
            )
            
            search_results, ask_result = await asyncio.gather(search_task, ask_task)
            
            # Extract raw Open Notebook IDs from search results
            upstream_ids = [res.get("id") for res in search_results if "id" in res]
            
            # 4. Map citations back to canonical Neosis UUIDs
            valid_source_ids, partial = await map_citations(upstream_ids, workspace_id, db)
            
            if not valid_source_ids:
                raise HTTPException(
                    status_code=422,
                    detail="ground_provenance_failure: Zero mapped canonical evidence."
                )
            
            return {
                "answer": ask_result.get("answer", ""),
                "evidence": valid_source_ids,
                "is_grounded": True,
                "provenance_status": "partial" if partial else "full"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Open Notebook Engine failed: {str(e)}")
            # Raise a clean exception, no legacy fallback or local synthesis
            raise HTTPException(status_code=503, detail="Upstream ground engine unavailable or synthesis failed.")
