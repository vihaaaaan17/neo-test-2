# ResearchRepository

> 56 nodes · cohesion 0.09

## Key Concepts

- **ResearchRepository** (46 connections) — `repositories/research.py`
- **UUID** (21 connections)
- **._verify_run_workspace()** (18 connections) — `repositories/research.py`
- **ResearchRun** (12 connections) — `models/research.py`
- **ResearchEvidence** (10 connections) — `models/research.py`
- **ResearchLifecycleService** (10 connections) — `services/research/lifecycle.py`
- **.batch_create_evidence()** (8 connections) — `repositories/research.py`
- **.transition_run()** (8 connections) — `services/research/lifecycle.py`
- **models/research.py** (7 connections) — `models/research.py`
- **Base** (7 connections)
- **ResearchTask** (7 connections) — `models/research.py`
- **ResearchArtifact** (6 connections) — `models/research.py`
- **ResearchReport** (6 connections) — `models/research.py`
- **ResearchUsage** (6 connections) — `models/research.py`
- **._bulk_insert_evidence()** (6 connections) — `repositories/research.py`
- **.transition_task()** (6 connections) — `services/research/lifecycle.py`
- **ResearchEvent** (5 connections) — `models/research.py`
- **.checkpoint_usage()** (5 connections) — `repositories/research.py`
- **.create_usage()** (5 connections) — `repositories/research.py`
- **._get_evidence_by_fingerprints()** (5 connections) — `repositories/research.py`
- **.create_artifact()** (4 connections) — `repositories/research.py`
- **.create_event()** (4 connections) — `repositories/research.py`
- **.create_evidence()** (4 connections) — `repositories/research.py`
- **.create_report()** (4 connections) — `repositories/research.py`
- **.create_task()** (4 connections) — `repositories/research.py`
- *... and 31 more nodes in this community*

## Relationships

- [run_research_agent_job](run_research_agent_job.md) (5 shared connections)
- [Source](Source.md) (3 shared connections)
- [ResearchQuotaService](ResearchQuotaService.md) (3 shared connections)
- [ResearchMetricsService](ResearchMetricsService.md) (3 shared connections)
- [create_research_run](create_research_run.md) (3 shared connections)
- [ProviderRateLimiter](ProviderRateLimiter.md) (2 shared connections)
- [workspaces.py](workspaces.py.md) (2 shared connections)
- [.admit_research_run](admit_research_run.md) (1 shared connections)
- [ResearchBudgetPolicy](ResearchBudgetPolicy.md) (1 shared connections)
- [get_workspace_metrics](get_workspace_metrics.md) (1 shared connections)
- [OpenDeepResearchEngine](OpenDeepResearchEngine.md) (1 shared connections)
- [GPTResearcherTool](GPTResearcherTool.md) (1 shared connections)

## Source Files

- `models/research.py`
- `repositories/research.py`
- `services/research/lifecycle.py`

## Audit Trail

- EXTRACTED: 133 (83%)
- INFERRED: 28 (17%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*