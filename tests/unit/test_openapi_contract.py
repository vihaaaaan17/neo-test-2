"""
Unit tests for OpenAPI contract freeze validation.

Validates:
- /openapi.json generates cleanly without ImportError or schema generation errors
- No internal implementation detail symbols leak into the public API surface
  (ODR = Open Deep Research, LangGraph, SurrealDB, asyncpg internals)
- All canonical schemas are present in the component definitions
"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from app.main import app
    return TestClient(app)


def test_openapi_schema_generates_without_error(client):
    """OpenAPI JSON must return 200 with a valid schema object."""
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    assert schema.get("openapi", "").startswith("3.")
    assert "info" in schema
    assert "paths" in schema
    assert "components" in schema


def test_no_internal_engine_symbols_in_schema(client):
    """
    Internal implementation symbols must not be exposed in the public OpenAPI schema.
    Forbidden: ODR internals, LangGraph types, SurrealDB connection types, asyncpg types.
    """
    resp = client.get("/openapi.json")
    schema_text = resp.text.lower()

    forbidden_symbols = [
        "asyncpg",           # DB driver implementation detail
        "surrealdb",         # internal graph DB
        "langgraph",         # internal orchestration framework
        "stategraph",        # LangGraph StateGraph type
        "groundmodestate",   # internal LangGraph state TypedDict
        "researchstate",     # internal LangGraph state TypedDict
        "researchcontext",   # internal Pydantic model for LangGraph
        "hybridretrievalservice",  # internal service class
    ]

    leaks = [sym for sym in forbidden_symbols if sym in schema_text]
    assert not leaks, (
        f"Internal implementation symbols leaked into OpenAPI schema: {leaks}\n"
        "These must not appear in /openapi.json. Ensure internal types are not "
        "used as FastAPI response_model or request body annotations."
    )


def test_canonical_schemas_present_in_components(client):
    """
    All canonical Chapter 4 domain schemas must be registered as OpenAPI components.
    """
    resp = client.get("/openapi.json")
    schema = resp.json()
    component_names = set(schema.get("components", {}).get("schemas", {}).keys())

    required_schemas = {
        "ConversationResponse",
        "TurnResponse",
        "ChatEventResponse",
        "PromotionCandidateResponse",
        "PromotionReviewResponse",
        "ScratchpadEntryResponse",
        "WorkspaceResponse",
        "WorkspaceCommitResponse",
    }

    missing = required_schemas - component_names
    assert not missing, (
        f"Required canonical schemas missing from OpenAPI components: {missing}\n"
        "All domain entities must be exposed as named components, not inline schemas."
    )


def test_canonical_api_paths_present(client):
    """
    All canonical Chapter 4 API paths must be present in the OpenAPI spec.
    """
    resp = client.get("/openapi.json")
    schema = resp.json()
    paths = set(schema.get("paths", {}).keys())

    required_path_prefixes = [
        "/api/v1/workspaces/{workspace_id}/conversations",
        "/api/v1/workspaces/{workspace_id}/promotions",
        "/api/v1/workspaces/{workspace_id}/conversations/{conversation_id}/scratchpad",
        "/api/v1/workspaces/{workspace_id}/commits",
        "/api/v1/workspaces/{workspace_id}/rollback",
    ]

    missing = [p for p in required_path_prefixes if not any(path.startswith(p.split("{")[0].rstrip("/")) for path in paths)]
    assert not missing, (
        f"Required canonical API path prefixes missing from OpenAPI spec: {missing}"
    )


def test_output_graph_schema_present(client):
    """
    OutputGraph and its sub-schemas must be registered as OpenAPI components.
    """
    resp = client.get("/openapi.json")
    schema = resp.json()
    component_names = set(schema.get("components", {}).get("schemas", {}).keys())

    output_graph_schemas = {"OutputGraph", "OutputGraphNode", "OutputGraphEdge"}
    missing = output_graph_schemas - component_names
    assert not missing, (
        f"OutputGraph schemas missing from OpenAPI components: {missing}"
    )


def test_research_run_schema_present(client):
    """ResearchRunResponse must be a named OpenAPI component."""
    resp = client.get("/openapi.json")
    schema = resp.json()
    component_names = set(schema.get("components", {}).get("schemas", {}).keys())
    assert "ResearchRunResponse" in component_names, (
        "ResearchRunResponse is missing from OpenAPI components. "
        "It must be a named schema so Chapter 5 clients can generate typed clients."
    )
