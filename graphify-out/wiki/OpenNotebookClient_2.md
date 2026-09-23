# OpenNotebookClient

> God node · 22 connections · `integrations/open_notebook/client.py`

**Community:** [OpenNotebookClient](OpenNotebookClient.md)

## Connections by Relation

### calls
- .__init__() `INFERRED`

### contains
- client.py `EXTRACTED`

### method
- ._get_headers() `EXTRACTED`
- ._get_client() `EXTRACTED`
- .get_health() `EXTRACTED`
- .get_default_models() `EXTRACTED`
- .search() `EXTRACTED`
- .ask_simple() `EXTRACTED`
- .chat_execute() `EXTRACTED`
- .create_notebook() `EXTRACTED`
- .upload_source() `EXTRACTED`
- .delete_source() `EXTRACTED`
- .delete_notebook() `EXTRACTED`
- .ask_stream() `EXTRACTED`
- .create_chat_session() `EXTRACTED`
- .__init__() `EXTRACTED`

### rationale_for
- HTTP client for communicating with the Open Notebook API. Establishes the… `EXTRACTED`

### uses
- chat_ground_mode() `INFERRED`
- OpenNotebookGroundEngine `INFERRED`
- project_to_open_notebook_job() `INFERRED`
- check_open_notebook_health() `INFERRED`
- process_deletion_tombstone_job() `INFERRED`

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*