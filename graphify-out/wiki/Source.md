# Source

> God node · 95 connections · `references/open-notebook/open_notebook/domain/notebook.py`

**Community:** [Community 1](Community_1.md)

## Connections by Relation

### calls
- _create_source_async_path() `EXTRACTED`
- _create_source_sync_path() `EXTRACTED`
- _call_model_with_source_context_inner() `EXTRACTED`
- make_source() `EXTRACTED`
- make_source() `EXTRACTED`
- .test_submit_generation_job_uses_notebook_context_content() `EXTRACTED`
- .test_real_source_full_text_reaches_formatted_prompt() `EXTRACTED`
- .get_sources() `EXTRACTED`
- .get_source() `EXTRACTED`
- .get_source() `EXTRACTED`
- .test_notebook_get_context_includes_source_full_text() `EXTRACTED`
- .test_notebook_get_context_propagates_source_errors() `EXTRACTED`
- .test_source_delete_cleans_up_file() `EXTRACTED`
- .test_source_delete_continues_on_file_error() `EXTRACTED`
- .test_vectorize_submits_command_with_valid_text() `EXTRACTED`
- _source() `EXTRACTED`
- make_source() `EXTRACTED`
- .test_source_delete_without_file() `EXTRACTED`
- .test_vectorize_raises_valueerror_when_empty_string() `EXTRACTED`
- .test_vectorize_raises_valueerror_when_no_text() `EXTRACTED`
- *…and 3 more `calls` connection(s) not listed (lowest-degree first to go)*

### contains
- notebook.py `EXTRACTED`

### imports
- sources.py `EXTRACTED`
- embedding_commands.py `EXTRACTED`
- test_domain.py `EXTRACTED`
- notebooks.py `EXTRACTED`
- test_utils.py `EXTRACTED`
- graphs/source_chat.py `EXTRACTED`
- graphs/source.py `EXTRACTED`
- context_builder.py `EXTRACTED`
- test_graphs.py `EXTRACTED`
- graphs/transformation.py `EXTRACTED`
- source_commands.py `EXTRACTED`
- test_add_insight_failure_propagation.py `EXTRACTED`
- _chat_shared.py `EXTRACTED`
- routers/embedding.py `EXTRACTED`
- test_source_path_containment.py `EXTRACTED`
- test_upload_type_mitigations.py `EXTRACTED`
- test_insight_timestamps.py `EXTRACTED`
- test_sources_api.py `EXTRACTED`
- test_recently_viewed_api.py `EXTRACTED`

### inherits
- ObjectModel `EXTRACTED`

### method
- .get_insights() `EXTRACTED`
- .delete() `EXTRACTED`
- .parse_command() `EXTRACTED`
- .get_processing_progress() `EXTRACTED`
- .get_embedded_chunks() `EXTRACTED`
- .add_insight() `EXTRACTED`
- .parse_id() `EXTRACTED`
- .get_status() `EXTRACTED`
- .get_context() `EXTRACTED`
- .add_to_notebook() `EXTRACTED`
- .vectorize() `EXTRACTED`
- ._prepare_save_data() `EXTRACTED`

### uses
- [InvalidInputError](InvalidInputError.md) `INFERRED`
- DatabaseOperationError `INFERRED`
- build_source_context() `INFERRED`
- TestBuildSourceContext `INFERRED`
- get_verified_source_session() `INFERRED`
- run_transformation() `INFERRED`
- TestNotebookDomain `INFERRED`
- retry_source_processing() `INFERRED`
- _source_to_response() `INFERRED`
- embed_content() `INFERRED`
- get_source() `INFERRED`
- TestSourceDomain `INFERRED`
- _is_source_file_available() `INFERRED`
- run_transformation_command() `INFERRED`
- build_notebook_context() `INFERRED`
- get_source_or_404() `INFERRED`
- add_source_to_notebook() `INFERRED`
- create_source_insight() `INFERRED`
- process_source_command() `INFERRED`
- save_source() `INFERRED`
- *…and 19 more `uses` connection(s) not listed (lowest-degree first to go)*

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*