# Community 201

> 15 nodes · cohesion 0.20

## Key Concepts

- **prepare_pinned_http_target()** (33 connections) — `references/open-notebook/open_notebook/utils/url_validation.py`
- **TestPinnedHttpTarget** (9 connections) — `references/open-notebook/tests/test_url_validation.py`
- **test_url_validation.py** (7 connections) — `references/open-notebook/tests/test_url_validation.py`
- **.test_unicode_hostname_idna_encoded_for_host_and_sni()** (4 connections) — `references/open-notebook/tests/test_url_validation.py`
- **.test_hostname_pinned_to_resolved_ip()** (3 connections) — `references/open-notebook/tests/test_url_validation.py`
- **.test_hostname_resolving_to_link_local_rejected()** (3 connections) — `references/open-notebook/tests/test_url_validation.py`
- **.test_https_sets_sni_hostname()** (3 connections) — `references/open-notebook/tests/test_url_validation.py`
- **.test_scoped_aws_imds_v6_rejected()** (3 connections) — `references/open-notebook/tests/test_url_validation.py`
- **.test_ip_literal_unchanged()** (2 connections) — `references/open-notebook/tests/test_url_validation.py`
- **.test_link_local_ip_rejected()** (2 connections) — `references/open-notebook/tests/test_url_validation.py`
- **Validate ``url``, resolve DNS once, and pin the outbound target to a vetted IP.…** (1 connections) — `references/open-notebook/open_notebook/utils/url_validation.py`
- **Test URL validation for SSRF protection in API key configuration. Note: The…** (1 connections) — `references/open-notebook/tests/test_url_validation.py`
- **DNS pinning closes the validate-then-httpx rebinding window.** (1 connections) — `references/open-notebook/tests/test_url_validation.py`
- **Scoped IMDSv6 literals must be rejected before pinning returns a target.** (1 connections) — `references/open-notebook/tests/test_url_validation.py`
- **Internationalized hostnames must use ASCII IDNA for Host and SNI.** (1 connections) — `references/open-notebook/tests/test_url_validation.py`

## Relationships

- [Community 0](Community_0.md) (13 shared connections)
- [Community 187](Community_187.md) (9 shared connections)
- [Community 294](Community_294.md) (4 shared connections)
- [Community 15](Community_15.md) (4 shared connections)
- [Community 26](Community_26.md) (1 shared connections)
- [Community 62](Community_62.md) (1 shared connections)

## Source Files

- `references/open-notebook/open_notebook/utils/url_validation.py`
- `references/open-notebook/tests/test_url_validation.py`

## Audit Trail

- EXTRACTED: 49 (92%)
- INFERRED: 4 (8%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*