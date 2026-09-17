import operator
from typing import TypedDict, Annotated, List
from uuid import UUID

class WorkingMemoryState(TypedDict):
    scratchpad: Annotated[List[str], operator.add]
    pinned_evidence: Annotated[List[UUID], operator.add]
    active_hypotheses: Annotated[List[str], operator.add]
