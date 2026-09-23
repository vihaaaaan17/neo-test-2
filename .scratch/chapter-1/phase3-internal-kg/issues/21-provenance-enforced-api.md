# 21: Provenance-Enforced Ground Mode API

**What to build:** The `POST /api/v1/workspaces/{id}/ask` endpoint that integrates the `GroundModeOrchestrator`. It enforces strict provenance by constraining the LLM to output Pydantic JSON containing the answer and discrete evidence references, rather than generic text. 

**Blocked by:** 19, 20

**Status:** done

- [x] A `POST /api/v1/workspaces/{id}/ask` endpoint is exposed.
- [x] The LLM call inside the Ground Mode orchestrator uses `response_format` or structured outputs to guarantee a `Pydantic` schema (`answer` string + `list[EvidenceRef]`).
- [x] The endpoint parses this JSON output and records the generated answer as a new `KnowledgeMemory` object in Postgres, strictly tagged with `source_mode="ground"`.
- [x] Creating the memory object automatically triggers the `arq` queue (Ticket 19) to sink this generated knowledge and its evidence edges into the Neo4j graph.
- [x] E2E tests confirm that querying the endpoint correctly retrieves sources, answers, returns structured JSON, and queues the sync job.
