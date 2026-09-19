# Community 118

> 25 nodes · cohesion 0.16

## Key Concepts

- **scraper.py** (23 connections) — `references/gpt-researcher/gpt_researcher/scraper/scraper.py`
- **validate_url()** (16 connections) — `references/gpt-researcher/gpt_researcher/utils/url_security.py`
- **UnsafeURLError** (12 connections) — `references/gpt-researcher/gpt_researcher/utils/url_security.py`
- **test_url_security.py** (11 connections) — `references/gpt-researcher/tests/test_url_security.py`
- **url_security.py** (9 connections) — `references/gpt-researcher/gpt_researcher/utils/url_security.py`
- **is_safe_url()** (7 connections) — `references/gpt-researcher/gpt_researcher/utils/url_security.py`
- **online_document.py** (6 connections) — `references/gpt-researcher/gpt_researcher/document/online_document.py`
- **test_rejects_non_http_and_local_paths()** (5 connections) — `references/gpt-researcher/tests/test_url_security.py`
- **test_rejects_internal_addresses()** (4 connections) — `references/gpt-researcher/tests/test_url_security.py`
- **_is_disallowed_ip()** (3 connections) — `references/gpt-researcher/gpt_researcher/utils/url_security.py`
- **test_allows_public_ip()** (3 connections) — `references/gpt-researcher/tests/test_url_security.py`
- **test_blocks_host_resolving_to_private_ip()** (3 connections) — `references/gpt-researcher/tests/test_url_security.py`
- **_private_urls_allowed()** (2 connections) — `references/gpt-researcher/gpt_researcher/utils/url_security.py`
- **parametrize** (2 connections)
- **test_allow_private_argument_bypasses_check()** (2 connections) — `references/gpt-researcher/tests/test_url_security.py`
- **test_allow_private_env_var_bypasses_check()** (2 connections) — `references/gpt-researcher/tests/test_url_security.py`
- **firecrawl/__init__.py** (1 connections) — `references/gpt-researcher/gpt_researcher/scraper/firecrawl/__init__.py`
- **Web scraper module for GPT Researcher. This module provides the Scraper class…** (1 connections) — `references/gpt-researcher/gpt_researcher/scraper/scraper.py`
- **ValueError** (1 connections)
- **URL security utilities for GPT Researcher. These helpers protect the scraping…** (1 connections) — `references/gpt-researcher/gpt_researcher/utils/url_security.py`
- **Return ``True`` if ``url`` passes :func:`validate_url`, else ``False``.** (1 connections) — `references/gpt-researcher/gpt_researcher/utils/url_security.py`
- **Raised when a URL is rejected by the SSRF / local-file protections.** (1 connections) — `references/gpt-researcher/gpt_researcher/utils/url_security.py`
- **Return True if the address is not safe to contact (i.e. internal).** (1 connections) — `references/gpt-researcher/gpt_researcher/utils/url_security.py`
- **Validate that ``url`` is safe to fetch and return it unchanged. Args: url: The…** (1 connections) — `references/gpt-researcher/gpt_researcher/utils/url_security.py`
- **Tests for the SSRF / local-file-read URL protections. These cover the guard…** (1 connections) — `references/gpt-researcher/tests/test_url_security.py`

## Relationships

- [Community 67](Community_67.md) (5 shared connections)
- [Community 227](Community_227.md) (4 shared connections)
- [Community 66](Community_66.md) (4 shared connections)
- [Community 48](Community_48.md) (3 shared connections)
- [Community 120](Community_120.md) (2 shared connections)
- [Community 226](Community_226.md) (1 shared connections)
- [Community 162](Community_162.md) (1 shared connections)
- [Community 133](Community_133.md) (1 shared connections)
- [Community 190](Community_190.md) (1 shared connections)
- [Community 137](Community_137.md) (1 shared connections)
- [Community 245](Community_245.md) (1 shared connections)
- [Community 243](Community_243.md) (1 shared connections)

## Source Files

- `references/gpt-researcher/gpt_researcher/document/online_document.py`
- `references/gpt-researcher/gpt_researcher/scraper/firecrawl/__init__.py`
- `references/gpt-researcher/gpt_researcher/scraper/scraper.py`
- `references/gpt-researcher/gpt_researcher/utils/url_security.py`
- `references/gpt-researcher/tests/test_url_security.py`

## Audit Trail

- EXTRACTED: 67 (93%)
- INFERRED: 5 (7%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*