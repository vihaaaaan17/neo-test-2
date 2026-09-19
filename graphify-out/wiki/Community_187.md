# Community 187

> 17 nodes · cohesion 0.12

## Key Concepts

- **TestPinnedHttpTargetSelfHostedUse** (10 connections) — `references/open-notebook/tests/test_url_validation.py`
- **.test_host_docker_internal_survives_pinning()** (4 connections) — `references/open-notebook/tests/test_url_validation.py`
- **.test_ipv6_only_host_pinned_with_brackets()** (4 connections) — `references/open-notebook/tests/test_url_validation.py`
- **.test_localhost_ollama_survives_pinning()** (4 connections) — `references/open-notebook/tests/test_url_validation.py`
- **.test_private_lan_hostname_survives_pinning()** (4 connections) — `references/open-notebook/tests/test_url_validation.py`
- **.test_query_string_and_path_preserved()** (4 connections) — `references/open-notebook/tests/test_url_validation.py`
- **.test_tailscale_cgnat_address_survives_pinning()** (4 connections) — `references/open-notebook/tests/test_url_validation.py`
- **.test_private_lan_ip_literal_survives_pinning()** (3 connections) — `references/open-notebook/tests/test_url_validation.py`
- **.test_ipv6_loopback_literal_survives_pinning()** (2 connections) — `references/open-notebook/tests/test_url_validation.py`
- **The pinning guard must not break the self-hosted setups it protects.…** (1 connections) — `references/open-notebook/tests/test_url_validation.py`
- **The single most common self-hosted setup: Ollama on localhost.** (1 connections) — `references/open-notebook/tests/test_url_validation.py`
- **Containerized app reaching a service on the host.** (1 connections) — `references/open-notebook/tests/test_url_validation.py`
- **LM Studio (or any box) addressed by private IP literal on the LAN.** (1 connections) — `references/open-notebook/tests/test_url_validation.py`
- **A LAN hostname resolving into RFC1918 space stays reachable.** (1 connections) — `references/open-notebook/tests/test_url_validation.py`
- **Tailscale hands out 100.64.0.0/10 — shared space, not link-local.** (1 connections) — `references/open-notebook/tests/test_url_validation.py`
- **An AAAA-only endpoint must produce a bracketed, parseable URL.** (1 connections) — `references/open-notebook/tests/test_url_validation.py`
- **PPQ-style discovery URLs carry a query string that must survive.** (1 connections) — `references/open-notebook/tests/test_url_validation.py`

## Relationships

- [Community 201](Community_201.md) (9 shared connections)
- [Community 15](Community_15.md) (6 shared connections)

## Source Files

- `references/open-notebook/tests/test_url_validation.py`

## Audit Trail

- EXTRACTED: 25 (81%)
- INFERRED: 6 (19%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*