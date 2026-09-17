import pytest
import pytest_asyncio
from uuid import uuid4
from app.schemas.graph import OutputGraph, OutputGraphNode, OutputGraphEdge, ProvenanceBundle
from app.repositories.graph import GraphRepository, graph_store

@pytest.fixture
def repo():
    return GraphRepository(graph_store)

@pytest.mark.asyncio
@pytest.mark.integration
async def test_output_graph_projection_and_retrieval(repo):
    workspace_id = uuid4()
    
    # 1. Create a graph
    ref1 = uuid4()
    ref2 = uuid4()
    
    node1 = OutputGraphNode(
        id="node_a",
        label="Concept",
        properties={"name": "Efficiency", "value": 18.3},
        provenance=ProvenanceBundle(
            derived_from_refs=[ref1, ref2],
            calculation="(1.42 / 1.20 - 1) * 100 = 18.3%",
            verification_status="Mathematically verified"
        )
    )
    
    node2 = OutputGraphNode(
        id="node_b",
        label="Finding",
        properties={"text": "New method is better"}
    )
    
    edge = OutputGraphEdge(
        source_id="node_b",
        target_id="node_a",
        type="DERIVES_FROM",
        properties={"confidence": 0.95}
    )
    
    graph = OutputGraph(nodes=[node1, node2], edges=[edge])
    
    # 2. Project it
    await repo.project_output_graph(workspace_id, graph)
    
    # 3. Retrieve it
    retrieved_graph = await repo.get_output_graph(workspace_id)
    
    # 4. Verify
    assert len(retrieved_graph.nodes) == 2
    assert len(retrieved_graph.edges) == 1
    
    ret_node1 = next(n for n in retrieved_graph.nodes if n.id == "node_a")
    assert ret_node1.label == "Concept"
    assert ret_node1.properties["name"] == "Efficiency"
    assert ret_node1.properties["value"] == 18.3
    
    assert ret_node1.provenance is not None
    assert ref1 in ret_node1.provenance.derived_from_refs
    assert ref2 in ret_node1.provenance.derived_from_refs
    assert ret_node1.provenance.calculation == "(1.42 / 1.20 - 1) * 100 = 18.3%"
    assert ret_node1.provenance.verification_status == "Mathematically verified"
    
    ret_node2 = next(n for n in retrieved_graph.nodes if n.id == "node_b")
    assert ret_node2.label == "Finding"
    assert ret_node2.provenance is None
    
    ret_edge = retrieved_graph.edges[0]
    assert ret_edge.source_id == "node_b"
    assert ret_edge.target_id == "node_a"
    assert ret_edge.type == "DERIVES_FROM"
    assert ret_edge.properties["confidence"] == 0.95
