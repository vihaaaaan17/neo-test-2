# 03: Neosis-Aware Retrievers and Evidence Interception

**What to build:** 
Inject distinct Neosis-aware tools (e.g., `web_search`, `academic_search`) into the ODR runtime. These tools intercept ODR's search calls, execute the underlying search via the provider neutral registry, and immediately persist the results into PostgreSQL as canonical `ResearchEvidence` records (linked to the `run_id`). They then return the raw stringified results to ODR so it can continue planning without losing provenance.

**Blocked by:** 02: ODR Adapter Skeleton and Event Normalization

**Status:** ready-for-agent

- [x] Create Neosis-aware tool wrappers for ODR in `app/integrations/research_engine/tools/`.
- [x] Implement tool logic to perform search and save `ResearchEvidence` via `ResearchRepository` before returning output.
- [x] Ensure tools enforce workspace source boundaries/policies.
- [x] Update `OpenDeepResearchEngine` to provide these custom tools to the ODR LangGraph.
