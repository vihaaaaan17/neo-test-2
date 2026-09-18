import json
import zipfile
import io
import pandas as pd
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.workspace import Workspace
from app.models.source import Source
from app.models.knowledge import KnowledgeMemory
from app.models.episodic import EpisodicMemory
from app.models.block import DocumentBlock
from app.services.storage import S3ObjectStore

class WorkspaceExportService:
    def __init__(self, db: AsyncSession, object_store: S3ObjectStore):
        self.db = db
        self.object_store = object_store
        
    async def export_to_zip(self, workspace_id: UUID) -> str:
        # 1. Fetch JSON metadata
        ws_result = await self.db.execute(select(Workspace).where(Workspace.workspace_id == workspace_id))
        workspace = ws_result.scalars().first()
        if not workspace:
            raise ValueError(f"Workspace {workspace_id} not found")
            
        sources_result = await self.db.execute(select(Source).where(Source.workspace_id == workspace_id))
        knowledge_result = await self.db.execute(select(KnowledgeMemory).where(KnowledgeMemory.workspace_id == workspace_id))
        episodic_result = await self.db.execute(select(EpisodicMemory).where(EpisodicMemory.workspace_id == workspace_id))
        
        # Serialize to dicts
        sources = list(sources_result.scalars())
        metadata = {
            "workspace": {"workspace_id": str(workspace.workspace_id), "status": workspace.status},
            "sources": [{"source_id": str(s.source_id), "source_type": s.source_type} for s in sources],
            "knowledge": [{"knowledge_id": str(k.knowledge_id), "content": k.content} for k in knowledge_result.scalars()],
            "episodic": [{"episode_id": str(e.episode_id), "summary": e.summary} for e in episodic_result.scalars()]
        }
        
        metadata_json = json.dumps(metadata, indent=2)
        
        # 2. Fetch Parquet Data (Chunks/Blocks)
        source_ids = [s.source_id for s in sources]
        
        block_data = []
        if source_ids:
            blocks_result = await self.db.execute(
                select(DocumentBlock).where(DocumentBlock.source_id.in_(source_ids))
            )
            blocks = blocks_result.scalars().all()
            
            for b in blocks:
                # Handle pgvector casting if necessary; pgvector arrays might be returned as strings or numpy arrays
                # We convert to a standard python list to ensure pyarrow serialization compatibility
                embedding_list = None
                if b.embedding is not None:
                    if hasattr(b.embedding, "tolist"):
                        embedding_list = b.embedding.tolist()
                    elif isinstance(b.embedding, str):
                        embedding_list = json.loads(b.embedding)
                    else:
                        embedding_list = list(b.embedding)
                        
                block_data.append({
                    "block_id": str(b.block_id),
                    "source_id": str(b.source_id),
                    "text_or_ref": b.text_or_ref,
                    "sequence": b.sequence,
                    "embedding": embedding_list
                })
            
        df = pd.DataFrame(block_data)
        # Ensure correct empty dataframe creation if no blocks exist
        if df.empty:
            df = pd.DataFrame(columns=["block_id", "source_id", "text_or_ref", "sequence", "embedding"])
            
        parquet_buffer = io.BytesIO()
        df.to_parquet(parquet_buffer, engine="pyarrow")
        parquet_bytes = parquet_buffer.getvalue()
        
        # 3. Zip it up
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("metadata.json", metadata_json)
            zf.writestr("chunks.parquet", parquet_bytes)
            
        zip_bytes = zip_buffer.getvalue()
        
        # 4. Upload to ObjectStore
        filename = f"export_{workspace_id}.zip"
        uri = await self.object_store.upload_file(workspace_id, zip_bytes, filename)
        
        # 5. Generate signed URL
        signed_url = await self.object_store.generate_presigned_url(uri)
        return signed_url
