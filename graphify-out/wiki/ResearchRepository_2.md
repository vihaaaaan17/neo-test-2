# ResearchRepository

> God node · 46 connections · `repositories/research.py`

**Community:** [ResearchRepository](ResearchRepository.md)

## Connections by Relation

### calls
- create_research_run() `INFERRED`
- run_research_agent_job() `INFERRED`
- get_queue_status() `INFERRED`
- get_quota_status() `INFERRED`
- neosis_web_search() `INFERRED`
- get_workspace_metrics() `INFERRED`
- .astream_events() `INFERRED`
- ._arun() `INFERRED`
- get_research_repository() `EXTRACTED`

### contains
- repositories/research.py `EXTRACTED`

### method
- ._verify_run_workspace() `EXTRACTED`
- .batch_create_evidence() `EXTRACTED`
- ._bulk_insert_evidence() `EXTRACTED`
- ._get_evidence_by_fingerprints() `EXTRACTED`
- .checkpoint_usage() `EXTRACTED`
- .create_usage() `EXTRACTED`
- .create_evidence() `EXTRACTED`
- .get_evidence() `EXTRACTED`
- .list_evidence_for_run() `EXTRACTED`
- .create_artifact() `EXTRACTED`
- .get_artifact() `EXTRACTED`
- .create_report() `EXTRACTED`
- .get_report() `EXTRACTED`
- .get_usage() `EXTRACTED`
- .create_event() `EXTRACTED`
- .get_events_for_run() `EXTRACTED`
- .create_task() `EXTRACTED`
- .get_task() `EXTRACTED`
- .__init__() `EXTRACTED`
- .create_run() `EXTRACTED`
- *…and 1 more `method` connection(s) not listed (lowest-degree first to go)*

### rationale_for
- Unified repository for all Research Fabric models. Enforces workspace_id… `EXTRACTED`

### references
- start_research() `EXTRACTED`
- .__init__() `EXTRACTED`
- .__init__() `EXTRACTED`
- .__init__() `EXTRACTED`
- .__init__() `EXTRACTED`
- .__init__() `EXTRACTED`
- .__init__() `EXTRACTED`

### uses
- ResearchRun `INFERRED`
- ResearchEvidence `INFERRED`
- ResearchTask `INFERRED`
- ResearchArtifact `INFERRED`
- ResearchReport `INFERRED`
- ResearchUsage `INFERRED`
- ResearchEvent `INFERRED`

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*