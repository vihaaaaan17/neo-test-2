# ensure_record_id()

> God node · 74 connections · `references/open-notebook/open_notebook/database/repository.py`

**Community:** [Community 36](Community_36.md)

## Connections by Relation

### calls
- generate_podcast_command() `EXTRACTED`
- _create_source_async_path() `EXTRACTED`
- get_verified_source_session() `EXTRACTED`
- execute_chat() `EXTRACTED`
- retry_source_processing() `EXTRACTED`
- .resolve() `EXTRACTED`
- get_session() `EXTRACTED`
- update_session() `EXTRACTED`
- delete_credential() `EXTRACTED`
- get_source() `EXTRACTED`
- update_notebook() `EXTRACTED`
- get_source_chat_sessions() `EXTRACTED`
- get_sources() `EXTRACTED`
- .get_display_info_for_ids() `EXTRACTED`
- resolve_notebook_scope() `EXTRACTED`
- add_source_to_notebook() `EXTRACTED`
- repo_update() `EXTRACTED`
- repo_upsert() `EXTRACTED`
- .get_job_details_for_commands() `EXTRACTED`
- get_notebook() `EXTRACTED`
- *…and 35 more `calls` connection(s) not listed (lowest-degree first to go)*

### contains
- repository.py `EXTRACTED`

### imports
- sources.py `EXTRACTED`
- notebook.py `EXTRACTED`
- credentials.py `EXTRACTED`
- embedding_commands.py `EXTRACTED`
- routers/chat.py `EXTRACTED`
- notebooks.py `EXTRACTED`
- routers/source_chat.py `EXTRACTED`
- ai/models.py `EXTRACTED`
- podcasts/models.py `EXTRACTED`
- domain/base.py `EXTRACTED`
- podcast_commands.py `EXTRACTED`
- credential.py `EXTRACTED`
- source_commands.py `EXTRACTED`
- _chat_shared.py `EXTRACTED`
- domain/transformation.py `EXTRACTED`
- provider_config.py `EXTRACTED`

### rationale_for
- Ensure a value is a RecordID. `EXTRACTED`

### references
- RecordID `EXTRACTED`

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*