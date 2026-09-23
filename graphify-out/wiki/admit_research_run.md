# .admit_research_run

> 4 nodes · cohesion 0.50

## Key Concepts

- **.admit_research_run()** (4 connections) — `services/research/admission.py`
- **admission.py** (3 connections) — `services/research/admission.py`
- **UUID** (2 connections)
- **Admits a new research run after checking quotas and rate limits.** (1 connections) — `services/research/admission.py`

## Relationships

- [ProviderRateLimiter](ProviderRateLimiter.md) (2 shared connections)
- [FastAPI](FastAPI.md) (1 shared connections)
- [ResearchRepository](ResearchRepository.md) (1 shared connections)

## Source Files

- `services/research/admission.py`

## Audit Trail

- EXTRACTED: 7 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*