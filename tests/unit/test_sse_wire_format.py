import pytest
from app.services.chat.events import format_sse_event

def test_format_sse_event_with_explicit_event_id():
    formatted = format_sse_event("token", {"content": "hello"}, event_id=42)
    assert formatted.startswith("id: 42\nevent: token\ndata: ")
    assert formatted.endswith("\n\n")

def test_format_sse_event_extracts_sequence_from_dict():
    formatted = format_sse_event("status_change", {"status": "completed", "sequence": 7})
    assert "id: 7\n" in formatted
    assert "event: status_change\n" in formatted

def test_format_sse_event_without_sequence_has_no_id():
    formatted = format_sse_event("ping", {"time": "now"})
    assert not formatted.startswith("id:")
    assert formatted.startswith("event: ping\ndata: ")
