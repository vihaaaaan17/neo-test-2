# InvalidInputError

> God node · 64 connections · `references/open-notebook/open_notebook/exceptions.py`

**Community:** [Community 6](Community_6.md)

## Connections by Relation

### calls
- resolve_notebook_scope() `EXTRACTED`
- vector_search() `EXTRACTED`
- .delete() `EXTRACTED`
- text_search() `EXTRACTED`
- _resolve_speaker_config() `EXTRACTED`
- .get() `EXTRACTED`
- .get_all() `EXTRACTED`
- ._validate_order_by() `EXTRACTED`
- .relate() `EXTRACTED`
- .delete() `EXTRACTED`
- .add_insight() `EXTRACTED`
- .relate_to_notebook() `EXTRACTED`
- .relate_to_source() `EXTRACTED`
- .add_to_notebook() `EXTRACTED`
- .content_must_not_be_empty() `EXTRACTED`
- .name_must_not_be_empty() `EXTRACTED`
- .add_to_notebook() `EXTRACTED`
- .test_update_source_invalid_input_still_returns_its_message() `EXTRACTED`

### contains
- exceptions.py `EXTRACTED`

### imports
- api/main.py `EXTRACTED`
- sources.py `EXTRACTED`
- notebook.py `EXTRACTED`
- routers/models.py `EXTRACTED`
- test_domain.py `EXTRACTED`
- notebooks.py `EXTRACTED`
- transformations.py `EXTRACTED`
- domain/base.py `EXTRACTED`
- search.py `EXTRACTED`
- episode_profiles.py `EXTRACTED`
- notes.py `EXTRACTED`
- test_add_insight_failure_propagation.py `EXTRACTED`
- test_search_api.py `EXTRACTED`
- insights.py `EXTRACTED`
- routers/settings.py `EXTRACTED`
- test_error_message_sanitization.py `EXTRACTED`
- test_order_by_validation.py `EXTRACTED`

### inherits
- [OpenNotebookError](OpenNotebookError.md) `EXTRACTED`

### rationale_for
- Raised when invalid input is provided. `EXTRACTED`

### uses
- [Source](Source.md) `INFERRED`
- Notebook `INFERRED`
- Note `INFERRED`
- ObjectModel `INFERRED`
- create_source() `INFERRED`
- TestNotebookDomain `INFERRED`
- search_knowledge_base() `INFERRED`
- ChatSession `INFERRED`
- update_notebook() `INFERRED`
- save_insight_as_note() `INFERRED`
- create_model() `INFERRED`
- create_note() `INFERRED`
- create_transformation() `INFERRED`
- create_notebook() `INFERRED`
- update_note() `INFERRED`
- update_settings() `INFERRED`
- update_transformation() `INFERRED`
- update_default_models() `INFERRED`
- update_source() `INFERRED`
- TestResolveNotebookScope `INFERRED`
- *…and 6 more `uses` connection(s) not listed (lowest-degree first to go)*

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*