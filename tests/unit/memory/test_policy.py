import pytest
from app.services.memory.policy import (
    GroundContextPolicy,
    ResearchContextPolicy,
    is_allowed_for_ground,
    is_allowed_for_research,
    filter_by_policy,
    MemoryItemType,
    GROUND_DENIED_TYPES,
)


def test_ground_denied_types_explicit():
    """
    Every denied entity type must return False for Ground mode.
    Ground is source-grounded and must never ingest research-derived state.
    """
    denied_list = [
        "KnowledgeMemory",
        "knowledge_memory",
        "ResearchEvidence",
        "research_evidence",
        "ResearchReport",
        "research_report",
        "OutputGraph",
        "output_graph",
        "ResearchScratchpad",
        "research_scratchpad",
        "ScratchpadEntry",
        "scratchpad_entry",
        "ResearchHypothesis",
        "research_hypothesis",
        "hypothesis",
        "unverified_candidate",
        "episodic_memory",
        "episodic",
        "research_turn",
        "research_conversation_turn",
    ]
    for item_type in denied_list:
        assert not is_allowed_for_ground(item_type), f"{item_type} must NOT be allowed for Ground mode"
        assert not GroundContextPolicy.is_allowed(item_type), f"{item_type} must be denied by GroundContextPolicy"


def test_ground_allowed_types():
    """
    Ground mode allows canonical sources, chunks, and prior ground turns.
    """
    allowed_list = [
        "source",
        "source_document",
        "source_chunk",
        "source_metadata",
        "ground_turn",
        "ground_conversation_turn",
        "current_query",
    ]
    for item_type in allowed_list:
        assert is_allowed_for_ground(item_type), f"{item_type} must be allowed for Ground mode"
        assert GroundContextPolicy.is_allowed(item_type), f"{item_type} must be allowed by GroundContextPolicy"


def test_research_allowed_types():
    """
    Research mode is state-aware and accepts broader context.
    """
    research_allowed = [
        "source",
        "ground_turn",
        "research_turn",
        "knowledge_memory",
        "research_evidence",
        "output_graph",
        "scratchpad",
        "working_memory",
        "pinned_evidence",
    ]
    for item_type in research_allowed:
        assert is_allowed_for_research(item_type), f"{item_type} must be allowed for Research mode"
        assert ResearchContextPolicy.is_allowed(item_type), f"{item_type} must be allowed by ResearchContextPolicy"


def test_filter_by_policy():
    """
    filter_by_policy strips all disallowed items according to the mode.
    """
    class MockItem:
        def __init__(self, item_id: str, item_type: str):
            self.id = item_id
            self.type = item_type

    items = [
        MockItem("1", "source_document"),
        MockItem("2", "knowledge_memory"),
        MockItem("3", "research_evidence"),
        MockItem("4", "ground_conversation_turn"),
        MockItem("5", "scratchpad_entry"),
        MockItem("6", "output_graph"),
    ]

    # Ground filtering: only items 1 and 4 allowed
    ground_filtered = filter_by_policy(items, mode="ground")
    assert [i.id for i in ground_filtered] == ["1", "4"]

    # Research filtering: all allowed
    research_filtered = filter_by_policy(items, mode="research")
    assert len(research_filtered) == len(items)


def test_filter_by_policy_invalid_mode():
    with pytest.raises(ValueError, match="Unknown mode"):
        filter_by_policy([], mode="invalid_mode")
