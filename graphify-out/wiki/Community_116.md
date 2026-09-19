# Community 116

> 26 nodes · cohesion 0.14

## Key Concepts

- **test_retriever_requires_scraping.py** (18 connections) — `references/gpt-researcher/tests/test_retriever_requires_scraping.py`
- **_make()** (9 connections) — `references/gpt-researcher/tests/test_retriever_requires_scraping.py`
- **BaseRetriever** (8 connections) — `references/gpt-researcher/gpt_researcher/retrievers/base.py`
- **_conductor()** (8 connections) — `references/gpt-researcher/tests/test_retriever_requires_scraping.py`
- **_run()** (7 connections) — `references/gpt-researcher/tests/test_retriever_requires_scraping.py`
- **test_declared_content_falls_back_to_scraping_when_empty()** (5 connections) — `references/gpt-researcher/tests/test_retriever_requires_scraping.py`
- **test_declared_scraping_keeps_long_snippets_scrapeable()** (5 connections) — `references/gpt-researcher/tests/test_retriever_requires_scraping.py`
- **test_undeclared_retriever_keeps_legacy_behaviour()** (5 connections) — `references/gpt-researcher/tests/test_retriever_requires_scraping.py`
- **retrievers/base.py** (4 connections) — `references/gpt-researcher/gpt_researcher/retrievers/base.py`
- **.search()** (4 connections) — `references/gpt-researcher/gpt_researcher/retrievers/base.py`
- **test_declared_content_is_used_without_scraping()** (4 connections) — `references/gpt-researcher/tests/test_retriever_requires_scraping.py`
- **test_rows_without_a_url_are_skipped()** (4 connections) — `references/gpt-researcher/tests/test_retriever_requires_scraping.py`
- **test_undeclared_short_content_still_scrapes()** (4 connections) — `references/gpt-researcher/tests/test_retriever_requires_scraping.py`
- **ABC** (2 connections)
- **test_base_class_requires_a_search_method()** (2 connections) — `references/gpt-researcher/tests/test_retriever_requires_scraping.py`
- **test_shipped_declarations()** (2 connections) — `references/gpt-researcher/tests/test_retriever_requires_scraping.py`
- **Any** (1 connections)
- **Shared contract for retrievers. Retrievers fall into two kinds, and the…** (1 connections) — `references/gpt-researcher/gpt_researcher/retrievers/base.py`
- **Optional base class documenting the retriever contract. Subclassing is not…** (1 connections) — `references/gpt-researcher/gpt_researcher/retrievers/base.py`
- **Return search results. With ``requires_scraping = True`` each item should carry…** (1 connections) — `references/gpt-researcher/gpt_researcher/retrievers/base.py`
- **parametrize** (1 connections)
- **Retrievers declare whether their results still need scraping (#1846, #1892).…** (1 connections) — `references/gpt-researcher/tests/test_retriever_requires_scraping.py`
- **The #1846 / #1892 regression: a >100 char snippet must not suppress scraping.** (1 connections) — `references/gpt-researcher/tests/test_retriever_requires_scraping.py`
- **requires_scraping=False but no content on this row -- still worth fetching.** (1 connections) — `references/gpt-researcher/tests/test_retriever_requires_scraping.py`
- **Third-party retrievers must be unaffected: >100 chars still means content.** (1 connections) — `references/gpt-researcher/tests/test_retriever_requires_scraping.py`
- *... and 1 more nodes in this community*

## Relationships

- [Community 16](Community_16.md) (3 shared connections)
- [Community 25](Community_25.md) (2 shared connections)
- [Community 168](Community_168.md) (1 shared connections)
- [Community 4](Community_4.md) (1 shared connections)

## Source Files

- `references/gpt-researcher/gpt_researcher/retrievers/base.py`
- `references/gpt-researcher/tests/test_retriever_requires_scraping.py`

## Audit Trail

- EXTRACTED: 52 (96%)
- INFERRED: 2 (4%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*