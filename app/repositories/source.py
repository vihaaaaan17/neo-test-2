from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.models.source import Source, SourceSnapshot

class SourceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_source_with_snapshot(
        self, 
        workspace_id: UUID, 
        owner_id: UUID, 
        file_uri: str, 
        filename: str, 
        size: int, 
        checksum_sha256: str
    ) -> Source:
        source = Source(
            workspace_id=workspace_id,
            owner_id=owner_id,
            source_type="document"
        )
        self.session.add(source)
        await self.session.flush()

        snapshot = SourceSnapshot(
            source_id=source.source_id,
            file_uri=file_uri,
            filename=filename,
            size=size,
            checksum_sha256=checksum_sha256
        )
        self.session.add(snapshot)
        await self.session.commit()

        result = await self.session.execute(
            select(Source).options(selectinload(Source.snapshots)).where(Source.source_id == source.source_id)
        )
        return result.scalars().first()
