from typing import List, Literal, Any
from pydantic import BaseModel, Field

MemoryItemType = Literal["episodic", "knowledge", "source", "working"]

class MemoryItem(BaseModel):
    id: str
    type: MemoryItemType
    text: str
    metadata: dict[str, Any] | None = None

class ContextBundle(BaseModel):
    budget: int
    total_tokens: int = 0
    items: List[MemoryItem] = Field(default_factory=list)
    evicted_items: List[MemoryItem] = Field(default_factory=list)

    def get_context_text(self) -> str:
        # Reconstruct into a single text block grouped by type or just chronological.
        # But for now, just output all items safely.
        blocks = []
        for item in self.items:
            blocks.append(f"--- [{item.type.upper()}] {item.id} ---\n{item.text}")
        return "\n\n".join(blocks)
