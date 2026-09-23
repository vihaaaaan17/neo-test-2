# 23: Output KG & Deep Provenance Schema Support

**What to build:** Structural updates to the Phase 3 backend to allow the LLM to save deeply enriched "Curated Graphs" directly into Neo4j without colliding with the Internal KG, enabling rich frontend hover-cards.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] Create `OutputGraphNode` and `OutputGraphEdge` Pydantic models in `app/schemas/graph.py`.
- [ ] Implement `ProvenanceBundle` schema (tracking `derived_from_refs`, `calculation`, and `verification_status`) and attach it as a property to the `OutputGraphNode`.
- [ ] Update `app/repositories/graph.py` (`GraphRepository`) to handle saving these new Output Node/Edge types into Neo4j using isolating labels (e.g., `OutputNode`, `[:DERIVES_FROM]`).
- [ ] Ensure the Cypher queries in the repository can flatten/serialize the `ProvenanceBundle` nested JSON into Neo4j node properties and deserialize them on retrieval.
