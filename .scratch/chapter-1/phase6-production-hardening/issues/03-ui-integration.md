# 03: Integrate Export Button in Streamlit

**What to build:** The user interface for the export feature. A button in the Streamlit app that enqueues the background export job, shows a loading state while waiting for the Redis pub/sub notification, and finally displays the presigned download link to the user.

**Blocked by:** 02: Create export_workspace_job worker

**Status:** ready-for-agent

- [ ] "Export Workspace Data" button added to the Streamlit UI (e.g., in the sidebar or workspace settings view).
- [ ] Clicking the button calls the API or directly enqueues `export_workspace_job`.
- [ ] UI polls or subscribes to the Redis channel `export:<workspace_id>` to wait for completion.
- [ ] A success message and clickable download link (or `st.download_button`) are presented to the user when the URL is received.
