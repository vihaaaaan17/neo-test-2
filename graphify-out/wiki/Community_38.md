# Community 38

> 59 nodes · cohesion 0.06

## Key Concepts

- **test_utils.py** (25 connections) — `references/open-notebook/tests/test_utils.py`
- **build_source_context()** (21 connections) — `references/open-notebook/open_notebook/utils/context_builder.py`
- **TestBuildSourceContext** (20 connections) — `references/open-notebook/tests/test_utils.py`
- **_call_model_with_source_context_inner()** (13 connections) — `references/open-notebook/open_notebook/graphs/source_chat.py`
- **_format_source_context()** (11 connections) — `references/open-notebook/open_notebook/graphs/source_chat.py`
- **_truncate_source_to_token_budget()** (11 connections) — `references/open-notebook/open_notebook/utils/context_builder.py`
- **asyncio** (9 connections)
- **.test_large_source_is_deterministically_and_explicitly_truncated()** (9 connections) — `references/open-notebook/tests/test_utils.py`
- **.test_missing_source_text_is_reported_honestly()** (9 connections) — `references/open-notebook/tests/test_utils.py`
- **.test_source_and_insights_shape()** (9 connections) — `references/open-notebook/tests/test_utils.py`
- **_mock_source()** (8 connections) — `references/open-notebook/tests/test_utils.py`
- **call_model_with_source_context()** (7 connections) — `references/open-notebook/open_notebook/graphs/source_chat.py`
- **_source_content_is_available()** (7 connections) — `references/open-notebook/open_notebook/graphs/source_chat.py`
- **_rendered_source_context_tokens()** (7 connections) — `references/open-notebook/open_notebook/utils/context_builder.py`
- **.test_large_source_reserves_budget_for_insights()** (7 connections) — `references/open-notebook/tests/test_utils.py`
- **.test_preserves_insights_that_fit_token_budget()** (7 connections) — `references/open-notebook/tests/test_utils.py`
- **.test_real_source_full_text_reaches_formatted_prompt()** (7 connections) — `references/open-notebook/tests/test_utils.py`
- **SourceChatState** (6 connections) — `references/open-notebook/open_notebook/graphs/source_chat.py`
- **format_source_context()** (6 connections) — `references/open-notebook/open_notebook/utils/context_builder.py`
- **.test_large_source_reuses_initial_tokenization()** (6 connections) — `references/open-notebook/tests/test_utils.py`
- **.test_missing_source_yields_empty_context()** (6 connections) — `references/open-notebook/tests/test_utils.py`
- **.test_tiny_budget_omits_source_with_explicit_status()** (6 connections) — `references/open-notebook/tests/test_utils.py`
- **Any** (5 connections)
- **_insight()** (5 connections) — `references/open-notebook/tests/test_utils.py`
- **.test_notice_only_budget_omits_source()** (5 connections) — `references/open-notebook/tests/test_utils.py`
- *... and 34 more nodes in this community*

## Relationships

- [Community 33](Community_33.md) (16 shared connections)
- [Community 13](Community_13.md) (13 shared connections)
- [Community 15](Community_15.md) (13 shared connections)
- [Community 1](Community_1.md) (7 shared connections)
- [Community 7](Community_7.md) (7 shared connections)
- [Community 78](Community_78.md) (4 shared connections)
- [Community 6](Community_6.md) (3 shared connections)
- [Community 168](Community_168.md) (1 shared connections)
- [Community 298](Community_298.md) (1 shared connections)

## Source Files

- `references/open-notebook/open_notebook/graphs/source_chat.py`
- `references/open-notebook/open_notebook/utils/context_builder.py`
- `references/open-notebook/tests/test_utils.py`

## Audit Trail

- EXTRACTED: 154 (88%)
- INFERRED: 21 (12%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*