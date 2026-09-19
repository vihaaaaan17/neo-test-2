# Community 102

> 29 nodes · cohesion 0.10

## Key Concepts

- **ExaSearch** (14 connections) — `references/gpt-researcher/gpt_researcher/retrievers/exa/exa.py`
- **test_exa_null_attrs.py** (8 connections) — `references/gpt-researcher/tests/test_exa_null_attrs.py`
- **test_exa_search_errors.py** (7 connections) — `references/gpt-researcher/tests/test_exa_search_errors.py`
- **exa.py** (6 connections) — `references/gpt-researcher/gpt_researcher/retrievers/exa/exa.py`
- **_searcher()** (5 connections) — `references/gpt-researcher/tests/test_exa_null_attrs.py`
- **.__init__()** (4 connections) — `references/gpt-researcher/gpt_researcher/retrievers/exa/exa.py`
- **.search()** (4 connections) — `references/gpt-researcher/gpt_researcher/retrievers/exa/exa.py`
- **.summary()** (4 connections) — `references/storm/knowledge_storm/interface.py`
- **.search()** (3 connections) — `references/gpt-researcher/gpt_researcher/retrievers/arxiv/arxiv.py`
- **.find_similar()** (3 connections) — `references/gpt-researcher/gpt_researcher/retrievers/exa/exa.py`
- **._retrieve_api_key()** (3 connections) — `references/gpt-researcher/gpt_researcher/retrievers/exa/exa.py`
- **_Client** (3 connections) — `references/gpt-researcher/tests/test_arxiv_null_fields.py`
- **.get_contents()** (2 connections) — `references/gpt-researcher/gpt_researcher/retrievers/exa/exa.py`
- **.results()** (2 connections) — `references/gpt-researcher/tests/test_arxiv_null_fields.py`
- **test_find_similar_skips_missing_url()** (2 connections) — `references/gpt-researcher/tests/test_exa_null_attrs.py`
- **test_get_contents_skips_missing_id()** (2 connections) — `references/gpt-researcher/tests/test_exa_null_attrs.py`
- **test_search_skips_missing_url_and_uses_summary_fallback()** (2 connections) — `references/gpt-researcher/tests/test_exa_null_attrs.py`
- **test_search_normalizes_hits()** (2 connections) — `references/gpt-researcher/tests/test_exa_search_errors.py`
- **test_search_swallows_client_errors()** (2 connections) — `references/gpt-researcher/tests/test_exa_search_errors.py`
- **test_search_tolerates_missing_results_list()** (2 connections) — `references/gpt-researcher/tests/test_exa_search_errors.py`
- **Performs the search :param query: :param max_results: :return:** (1 connections) — `references/gpt-researcher/gpt_researcher/retrievers/arxiv/arxiv.py`
- **Retrieves the contents of the specified IDs using the Exa API. Args: ids: The…** (1 connections) — `references/gpt-researcher/gpt_researcher/retrievers/exa/exa.py`
- **Initializes the ExaSearch object. Args: query: The search query.** (1 connections) — `references/gpt-researcher/gpt_researcher/retrievers/exa/exa.py`
- **Retrieves the Exa API key from environment variables. Returns: The API key.…** (1 connections) — `references/gpt-researcher/gpt_researcher/retrievers/exa/exa.py`
- **Searches the query using the Exa API. Args: max_results: The maximum number of…** (1 connections) — `references/gpt-researcher/gpt_researcher/retrievers/exa/exa.py`
- *... and 4 more nodes in this community*

## Relationships

- [Community 106](Community_106.md) (4 shared connections)
- [Community 160](Community_160.md) (3 shared connections)
- [Community 168](Community_168.md) (2 shared connections)
- [Community 178](Community_178.md) (1 shared connections)
- [Community 123](Community_123.md) (1 shared connections)

## Source Files

- `references/gpt-researcher/gpt_researcher/retrievers/arxiv/arxiv.py`
- `references/gpt-researcher/gpt_researcher/retrievers/exa/exa.py`
- `references/gpt-researcher/tests/test_arxiv_null_fields.py`
- `references/gpt-researcher/tests/test_exa_null_attrs.py`
- `references/gpt-researcher/tests/test_exa_search_errors.py`
- `references/storm/knowledge_storm/interface.py`

## Audit Trail

- EXTRACTED: 42 (84%)
- INFERRED: 8 (16%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*