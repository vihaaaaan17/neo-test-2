from enum import Enum
from typing import Any, List, Set, Union


class MemoryItemType(str, Enum):
    # Canonical Ground sources
    SOURCE_DOCUMENT = "source_document"
    SOURCE_CHUNK = "source_chunk"
    SOURCE_METADATA = "source_metadata"
    GROUND_CONVERSATION_TURN = "ground_conversation_turn"
    
    # Research / Derived artifacts
    KNOWLEDGE_MEMORY = "knowledge_memory"
    RESEARCH_EVIDENCE = "research_evidence"
    RESEARCH_REPORT = "research_report"
    OUTPUT_GRAPH = "output_graph"
    RESEARCH_SCRATCHPAD = "research_scratchpad"
    RESEARCH_HYPOTHESIS = "research_hypothesis"
    UNVERIFIED_CANDIDATE = "unverified_candidate"
    EPISODIC_MEMORY = "episodic_memory"
    RESEARCH_CONVERSATION_TURN = "research_conversation_turn"
    
    # Working state
    WORKING_MEMORY = "working_memory"
    PINNED_EVIDENCE = "pinned_evidence"


# Explicit Denylist for Ground mode
GROUND_DENIED_TYPES: Set[str] = {
    MemoryItemType.KNOWLEDGE_MEMORY.value,
    MemoryItemType.RESEARCH_EVIDENCE.value,
    MemoryItemType.RESEARCH_REPORT.value,
    MemoryItemType.OUTPUT_GRAPH.value,
    MemoryItemType.RESEARCH_SCRATCHPAD.value,
    MemoryItemType.RESEARCH_HYPOTHESIS.value,
    MemoryItemType.UNVERIFIED_CANDIDATE.value,
    MemoryItemType.EPISODIC_MEMORY.value,
    MemoryItemType.RESEARCH_CONVERSATION_TURN.value,
    "knowledgememory",
    "researchevidence",
    "researchreport",
    "outputgraph",
    "researchscratchpad",
    "researchhypothesis",
    "scratchpadentry",
    "scratchpad_entry",
    "scratchpad",
    "hypothesis",
    "unverified_candidate",
    "episodic",
    "episodic_memory",
    "research_turn",
}

# Explicit Allowlist for Ground mode
GROUND_ALLOWED_TYPES: Set[str] = {
    MemoryItemType.SOURCE_DOCUMENT.value,
    MemoryItemType.SOURCE_CHUNK.value,
    MemoryItemType.SOURCE_METADATA.value,
    MemoryItemType.GROUND_CONVERSATION_TURN.value,
    "source",
    "source_document",
    "source_chunk",
    "source_metadata",
    "ground_turn",
    "ground_conversation_turn",
    "current_query",
}

# Allowlist for Research mode
RESEARCH_ALLOWED_TYPES: Set[str] = {
    MemoryItemType.SOURCE_DOCUMENT.value,
    MemoryItemType.SOURCE_CHUNK.value,
    MemoryItemType.SOURCE_METADATA.value,
    MemoryItemType.GROUND_CONVERSATION_TURN.value,
    MemoryItemType.RESEARCH_CONVERSATION_TURN.value,
    MemoryItemType.KNOWLEDGE_MEMORY.value,
    MemoryItemType.RESEARCH_EVIDENCE.value,
    MemoryItemType.OUTPUT_GRAPH.value,
    MemoryItemType.RESEARCH_SCRATCHPAD.value,
    MemoryItemType.RESEARCH_HYPOTHESIS.value,
    MemoryItemType.WORKING_MEMORY.value,
    MemoryItemType.PINNED_EVIDENCE.value,
    MemoryItemType.EPISODIC_MEMORY.value,
    "source",
    "source_document",
    "source_chunk",
    "source_metadata",
    "ground_turn",
    "ground_conversation_turn",
    "research_turn",
    "research_conversation_turn",
    "knowledge",
    "knowledge_memory",
    "knowledgememory",
    "research_evidence",
    "researchevidence",
    "research_report",
    "researchreport",
    "output_graph",
    "outputgraph",
    "scratchpad",
    "scratchpad_entry",
    "scratchpadentry",
    "working",
    "working_memory",
    "pinned_evidence",
    "episodic",
    "episodic_memory",
    "current_query",
    "current_message",
}


class GroundContextPolicy:
    """
    Policy governing data and memory eligibility for Ground mode execution.
    Ground is source-grounded: only canonical source documents, source chunks,
    and prior Ground conversation turns may be admitted.
    """
    @staticmethod
    def is_allowed(item_type: str) -> bool:
        normalized = item_type.lower().strip()
        if normalized in GROUND_DENIED_TYPES:
            return False
        return normalized in GROUND_ALLOWED_TYPES

    @staticmethod
    def filter_items(items: List[Any]) -> List[Any]:
        filtered = []
        for item in items:
            t = getattr(item, "type", None) or getattr(item, "item_type", None) or getattr(item, "source_mode", None) or str(type(item).__name__)
            if GroundContextPolicy.is_allowed(str(t)):
                filtered.append(item)
        return filtered


class ResearchContextPolicy:
    """
    Policy governing data and memory eligibility for Research mode execution.
    Research is state-aware: permitted to inspect working state, scratchpad,
    prior conversation turns, accepted knowledge, and research evidence.
    """
    @staticmethod
    def is_allowed(item_type: str) -> bool:
        normalized = item_type.lower().strip()
        return normalized in RESEARCH_ALLOWED_TYPES

    @staticmethod
    def filter_items(items: List[Any]) -> List[Any]:
        filtered = []
        for item in items:
            t = getattr(item, "type", None) or getattr(item, "item_type", None) or getattr(item, "source_mode", None) or str(type(item).__name__)
            if ResearchContextPolicy.is_allowed(str(t)):
                filtered.append(item)
        return filtered


def is_allowed_for_ground(item_type: str) -> bool:
    return GroundContextPolicy.is_allowed(item_type)


def is_allowed_for_research(item_type: str) -> bool:
    return ResearchContextPolicy.is_allowed(item_type)


def filter_by_policy(items: List[Any], mode: str) -> List[Any]:
    if mode == "ground":
        return GroundContextPolicy.filter_items(items)
    elif mode == "research":
        return ResearchContextPolicy.filter_items(items)
    else:
        raise ValueError(f"Unknown mode: {mode}")
