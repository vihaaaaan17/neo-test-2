# Community 155

> 20 nodes · cohesion 0.16

## Key Concepts

- **asyncio** (8 connections)
- **patch** (8 connections)
- **TestAsyncSourceAssetPersistence** (6 connections) — `references/open-notebook/tests/test_sources_api.py`
- **TestTitleSortUsesAlias** (5 connections) — `references/open-notebook/tests/test_sources_api.py`
- **.test_async_link_source_persists_url_asset()** (4 connections) — `references/open-notebook/tests/test_sources_api.py`
- **.test_async_text_source_has_no_asset()** (4 connections) — `references/open-notebook/tests/test_sources_api.py`
- **.test_async_upload_source_persists_file_asset()** (4 connections) — `references/open-notebook/tests/test_sources_api.py`
- **.test_get_missing_source_returns_404()** (4 connections) — `references/open-notebook/tests/test_sources_api.py`
- **TestRetrySourceProcessing** (4 connections) — `references/open-notebook/tests/test_sources_api.py`
- **.test_retry_400_only_when_truly_unlinked()** (3 connections) — `references/open-notebook/tests/test_sources_api.py`
- **.test_retry_finds_notebooks_and_requeues()** (3 connections) — `references/open-notebook/tests/test_sources_api.py`
- **.test_all_sort_fields_return_200()** (3 connections) — `references/open-notebook/tests/test_sources_api.py`
- **.test_sort_by_title_orders_by_alias()** (3 connections) — `references/open-notebook/tests/test_sources_api.py`
- **POST /sources with type=text and async_processing=true has asset=None.** (1 connections) — `references/open-notebook/tests/test_sources_api.py`
- **POST /sources/{id}/retry must find a source's notebooks via the reference…** (1 connections) — `references/open-notebook/tests/test_sources_api.py`
- **Tests for #627 - asset is persisted before async processing. These tests hit…** (1 connections) — `references/open-notebook/tests/test_sources_api.py`
- **Regression for sort_by=title returning a 500 (v1.11 release testing).…** (1 connections) — `references/open-notebook/tests/test_sources_api.py`
- **POST /sources with type=link and async_processing=true persists Asset(url=...).** (1 connections) — `references/open-notebook/tests/test_sources_api.py`
- **POST /sources with type=upload and async_processing=true persists…** (1 connections) — `references/open-notebook/tests/test_sources_api.py`
- **.test_invalid_sort_field_returns_400()** (1 connections) — `references/open-notebook/tests/test_sources_api.py`

## Relationships

- [Community 13](Community_13.md) (5 shared connections)
- [Community 1](Community_1.md) (1 shared connections)

## Source Files

- `references/open-notebook/tests/test_sources_api.py`

## Audit Trail

- EXTRACTED: 35 (97%)
- INFERRED: 1 (3%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*