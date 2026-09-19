# Community 192

> 16 nodes · cohesion 0.14

## Key Concepts

- **TestProviderRegistryIsTheSourceOfTruth** (9 connections) — `references/open-notebook/tests/test_credential_provider_validation.py`
- **ProviderSpec** (7 connections) — `references/open-notebook/open_notebook/ai/provider_registry.py`
- **_build_registry()** (5 connections) — `references/open-notebook/open_notebook/ai/provider_registry.py`
- **.test_registry_rejects_duplicate_provider_names()** (4 connections) — `references/open-notebook/tests/test_credential_provider_validation.py`
- **.env_config()** (2 connections) — `references/open-notebook/open_notebook/ai/provider_registry.py`
- **.test_openai_compat_discovery_urls_are_exactly_as_expected()** (2 connections) — `references/open-notebook/tests/test_credential_provider_validation.py`
- **Build the name -> spec map, refusing duplicate names at import time. A plain…** (1 connections) — `references/open-notebook/open_notebook/ai/provider_registry.py`
- **Everything the backend needs to know about one AI provider.** (1 connections) — `references/open-notebook/open_notebook/ai/provider_registry.py`
- **Env var config in the legacy PROVIDER_ENV_CONFIG dict shape.** (1 connections) — `references/open-notebook/open_notebook/ai/provider_registry.py`
- **Pin the derived provider -> discovery URL mapping so a registry edit can't…** (1 connections) — `references/open-notebook/tests/test_credential_provider_validation.py`
- **The registry drives every backend surface; the Literal is the only manual copy…** (1 connections) — `references/open-notebook/tests/test_credential_provider_validation.py`
- **A plain dict comprehension would silently drop the earlier spec on a name…** (1 connections) — `references/open-notebook/tests/test_credential_provider_validation.py`
- **.test_discovery_functions_cover_registry()** (1 connections) — `references/open-notebook/tests/test_credential_provider_validation.py`
- **.test_literal_matches_registry_keys()** (1 connections) — `references/open-notebook/tests/test_credential_provider_validation.py`
- **.test_registry_matches_known_good_provider_list()** (1 connections) — `references/open-notebook/tests/test_credential_provider_validation.py`
- **.test_registry_specs_are_internally_consistent()** (1 connections) — `references/open-notebook/tests/test_credential_provider_validation.py`

## Relationships

- [Community 127](Community_127.md) (3 shared connections)
- [Community 0](Community_0.md) (2 shared connections)

## Source Files

- `references/open-notebook/open_notebook/ai/provider_registry.py`
- `references/open-notebook/tests/test_credential_provider_validation.py`

## Audit Trail

- EXTRACTED: 21 (95%)
- INFERRED: 1 (5%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*