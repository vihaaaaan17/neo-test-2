# ResearchNormalizationService

> 10 nodes · cohesion 0.27

## Key Concepts

- **ResearchNormalizationService** (14 connections) — `services/research/normalization.py`
- **.generate_fingerprint()** (4 connections) — `services/research/normalization.py`
- **.normalize_evidence()** (4 connections) — `services/research/normalization.py`
- **.normalize_url()** (4 connections) — `services/research/normalization.py`
- **.__init__()** (3 connections) — `services/research/retrievers/academic.py`
- **normalization.py** (1 connections) — `services/research/normalization.py`
- **Normalizes a URL by parsing it, lowercasing the scheme and netloc, and sorting…** (1 connections) — `services/research/normalization.py`
- **Generates a SHA-256 fingerprint from the normalized URL and text content. Used…** (1 connections) — `services/research/normalization.py`
- **Normalizes evidence and computes a deduplicating SHA-256 fingerprint.** (1 connections) — `services/research/normalization.py`
- **Normalizes and deduplicates incoming research data.** (1 connections) — `services/research/normalization.py`

## Relationships

- [GPTResearcherRetriever](GPTResearcherRetriever.md) (2 shared connections)
- [MCPRetriever](MCPRetriever.md) (2 shared connections)
- [WebRetriever](WebRetriever.md) (2 shared connections)
- [ResearchSourceResult](ResearchSourceResult.md) (2 shared connections)
- [neosis_web_search](neosis_web_search.md) (1 shared connections)
- [UsageTracker](UsageTracker.md) (1 shared connections)

## Source Files

- `services/research/normalization.py`
- `services/research/retrievers/academic.py`

## Audit Trail

- EXTRACTED: 13 (59%)
- INFERRED: 9 (41%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*