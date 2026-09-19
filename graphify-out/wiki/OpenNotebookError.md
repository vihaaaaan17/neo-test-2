# OpenNotebookError

> God node · 151 connections · `references/open-notebook/open_notebook/exceptions.py`

**Community:** [Community 1](Community_1.md)

## Connections by Relation

### contains
- exceptions.py `EXTRACTED`

### imports
- api/main.py `EXTRACTED`
- sources.py `EXTRACTED`
- routers/models.py `EXTRACTED`
- credentials.py `EXTRACTED`
- routers/chat.py `EXTRACTED`
- notebooks.py `EXTRACTED`
- routers/source_chat.py `EXTRACTED`
- podcasts.py `EXTRACTED`
- transformations.py `EXTRACTED`
- graphs/source_chat.py `EXTRACTED`
- search.py `EXTRACTED`
- ask.py `EXTRACTED`
- episode_profiles.py `EXTRACTED`
- notes.py `EXTRACTED`
- graphs/transformation.py `EXTRACTED`
- error_classifier.py `EXTRACTED`
- graphs/chat.py `EXTRACTED`
- routers/embedding.py `EXTRACTED`
- embedding_rebuild.py `EXTRACTED`
- insights.py `EXTRACTED`
- *…and 3 more `imports` connection(s) not listed (lowest-degree first to go)*

### inherits
- [InvalidInputError](InvalidInputError.md) `EXTRACTED`
- NotFoundError `EXTRACTED`
- DatabaseOperationError `EXTRACTED`
- ConfigurationError `EXTRACTED`
- ExternalServiceError `EXTRACTED`
- UnsupportedTypeException `EXTRACTED`
- AuthenticationError `EXTRACTED`
- NetworkError `EXTRACTED`
- RateLimitError `EXTRACTED`
- FileOperationError `EXTRACTED`
- NoTranscriptFound `EXTRACTED`
- Exception `EXTRACTED`

### rationale_for
- Base exception class for Open Notebook errors. `EXTRACTED`

### uses
- classify_error() `INFERRED`
- list_podcast_episodes() `INFERRED`
- update_credential() `INFERRED`
- _create_source_async_path() `INFERRED`
- create_source() `INFERRED`
- provide_answer() `INFERRED`
- run_transformation() `INFERRED`
- call_model_with_messages() `INFERRED`
- execute_chat() `INFERRED`
- create_credential() `INFERRED`
- get_podcast_episode() `INFERRED`
- search_knowledge_base() `INFERRED`
- retry_source_processing() `INFERRED`
- get_session() `INFERRED`
- update_session() `INFERRED`
- delete_credential() `INFERRED`
- embed_content() `INFERRED`
- get_source() `INFERRED`
- build_context() `INFERRED`
- update_notebook() `INFERRED`
- *…and 94 more `uses` connection(s) not listed (lowest-degree first to go)*

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*