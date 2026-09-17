from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.block import DocumentBlock
from app.schemas.block import DocumentBlockCreate

class BlockRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def bulk_create_blocks(self, source_id: UUID, snapshot_id: UUID, blocks: list[DocumentBlockCreate]) -> list[DocumentBlock]:
        db_blocks = []
        for block_in in blocks:
            db_block = DocumentBlock(
                source_id=source_id,
                snapshot_id=snapshot_id,
                block_type=block_in.block_type,
                sequence=block_in.sequence,
                text_or_ref=block_in.text_or_ref,
                page_number=block_in.page_number,
                metadata_=block_in.metadata_
            )
            self.session.add(db_block)
            db_blocks.append(db_block)
        
        await self.session.commit()
        return db_blocks
