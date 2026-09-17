# GATES: 17 - Local Neo4j Setup & GraphStore Adapter

- [x] `docker-compose.yml` includes a Neo4j service.
  CHECK: powershell -c "Select-String -Pattern 'neo4j:' -Path docker-compose.yml"
  EXPECT: neo4j:
  EVIDENCE: Updated docker-compose.yml with neo4j:5 service.
- [x] Neo4j container can start and run successfully.
  CHECK: docker ps --format "{{.Names}}" | Select-String "neo4j"
  EXPECT: neo4j
  EVIDENCE: Output is 'neosislm-neo4j-1' and running on port 7474, 7687.
- [x] `GraphStore` abstract base class is defined.
  CHECK: powershell -c "Select-String -Pattern 'class GraphStore' -Path app/repositories/graph.py"
  EXPECT: class GraphStore
  EVIDENCE: Defined in app/repositories/graph.py
- [x] `Neo4jAdapter` implementation connects using `.env` credentials.
  CHECK: powershell -c "Select-String -Pattern 'class Neo4jAdapter' -Path app/repositories/graph.py"
  EXPECT: class Neo4jAdapter
  EVIDENCE: Defined Neo4jAdapter using settings.NEO4J_URI/USER/PASSWORD.
- [x] FastAPI lifespan handles Neo4j connection.
  CHECK: powershell -c "Select-String -Pattern 'GraphStore.connect()' -Path app/main.py"
  EXPECT: connect
  EVIDENCE: Awaits graph_store.connect() and .close() in lifespan.
- [x] Health check endpoint verifies Neo4j connection.
  CHECK: curl -s http://localhost:8000/health
  EXPECT: ok
  EVIDENCE: Python urllib returns {"status":"ok","postgres":"ok","neo4j":"ok"}
