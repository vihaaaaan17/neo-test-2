from pydantic import BaseModel, ConfigDict
from uuid import UUID
from typing import Any, Optional

class DocumentBlockCreate(BaseModel):
    block_type: str
    sequence: int
    text_or_ref: str
    page_number: Optional[int] = None
    metadata_: Optional[dict[str, Any]] = None

class DocumentBlockResponse(DocumentBlockCreate):
    block_id: UUID
    source_id: UUID
    snapshot_id: UUID

    model_config = ConfigDict(from_attributes=True)
