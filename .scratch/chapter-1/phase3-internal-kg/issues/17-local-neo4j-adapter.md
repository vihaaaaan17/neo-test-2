# 17: Local Neo4j Setup & GraphStore Adapter

**What to build:** A running Neo4j Docker container configured in `docker-compose.yml`, alongside a clean `GraphStore` Python adapter interface. This establishes the baseline connection to our Internal KG without tightly coupling the app to a specific provider driver.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] `docker-compose.yml` includes a local Neo4j container with persistent volume and auth configured.
- [ ] A `GraphStore` abstract base class is defined in `app/repositories/graph.py` or similar.
- [ ] A `Neo4jAdapter` implementation successfully connects to the local Neo4j container using credentials from `.env`.
- [ ] FastAPI lifespan gracefully handles the Neo4j driver connection (connects on startup, closes on shutdown).
- [ ] A basic health check endpoint verifies the Neo4j connection is active.
