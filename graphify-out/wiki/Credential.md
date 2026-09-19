# Credential

> God node · 70 connections · `references/open-notebook/open_notebook/domain/credential.py`

**Community:** [Community 0](Community_0.md)

## Connections by Relation

### calls
- migrate_from_provider_config() `EXTRACTED`
- create_credential_from_env() `EXTRACTED`
- test_credential_config_preserves_anthropic_compatible_fields() `EXTRACTED`
- .test_num_ctx_absent_when_unset() `EXTRACTED`
- .test_num_ctx_included_when_set() `EXTRACTED`
- .test_non_vertex_provider_keeps_generic_keys() `EXTRACTED`
- .test_vertex_emits_vertex_prefixed_keys() `EXTRACTED`
- .test_clearing_num_ctx_keeps_other_config_keys() `EXTRACTED`
- .test_db_row_with_config_lifts_num_ctx_to_top_level() `EXTRACTED`
- .test_mirrored_num_ctx_is_validated_as_int() `EXTRACTED`
- .test_null_config_loads_without_extras() `EXTRACTED`
- .test_num_ctx_round_trips_through_save_and_load() `EXTRACTED`
- .test_prepare_save_data_config_none_when_no_extras() `EXTRACTED`
- .test_prepare_save_data_packs_num_ctx_into_config() `EXTRACTED`
- .test_unmapped_config_keys_are_preserved_on_save() `EXTRACTED`

### contains
- credential.py `EXTRACTED`

### imports
- routers/models.py `EXTRACTED`
- credentials_service.py `EXTRACTED`
- credentials.py `EXTRACTED`
- model_discovery.py `EXTRACTED`
- test_domain.py `EXTRACTED`
- ai/models.py `EXTRACTED`
- test_anthropic_compatible_provider.py `EXTRACTED`
- test_podcast_anthropic_compatible.py `EXTRACTED`
- test_credentials_api.py `EXTRACTED`
- key_provider.py `EXTRACTED`
- test_vertex_credentials_file_oracle.py `EXTRACTED`
- test_order_by_validation.py `EXTRACTED`

### inherits
- ObjectModel `EXTRACTED`

### method
- .get_by_provider() `EXTRACTED`
- .get() `EXTRACTED`
- .get_all() `EXTRACTED`
- ._from_db_row() `EXTRACTED`
- .get_linked_models() `EXTRACTED`
- ._prepare_save_data() `EXTRACTED`
- .save() `EXTRACTED`
- ._mirror_config_to_fields() `EXTRACTED`
- .to_esperanto_config() `EXTRACTED`

### rationale_for
- Individual credential record for an AI provider. Each record stores… `EXTRACTED`

### uses
- Model `INFERRED`
- update_credential() `INFERRED`
- test_credential() `INFERRED`
- create_credential() `INFERRED`
- delete_credential() `INFERRED`
- credential_to_response() `INFERRED`
- TestCredentialConfigBag `INFERRED`
- migrate_from_env() `INFERRED`
- discover_models_for_credential() `INFERRED`
- _get_default_credential() `INFERRED`
- list_credentials() `INFERRED`
- get_provider_status() `INFERRED`
- register_models() `INFERRED`
- get_credential() `INFERRED`
- list_credentials_by_provider() `INFERRED`
- discover_anthropic_compatible_models() `INFERRED`
- discover_omlx_models() `INFERRED`
- discover_openai_compatible_models() `INFERRED`
- test_model_manager_maps_normalized_url_to_anthropic_factory() `INFERRED`
- test_model_manager_rejects_missing_compatible_endpoint() `INFERRED`
- *…and 11 more `uses` connection(s) not listed (lowest-degree first to go)*

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*