import abc
import logging
import json
from uuid import UUID
from typing import Any
from neo4j import AsyncGraphDatabase, AsyncDriver
from app.schemas.graph import OutputGraph, OutputGraphNode, OutputGraphEdge, ProvenanceBundle

logger = logging.getLogger(__name__)

class GraphStore(abc.ABC):
    """
    Abstract base class for our operational Knowledge Graph.
    This hides the provider-specific driver details (e.g. Neo4j).
    """

    @abc.abstractmethod
    async def connect(self) -> None:
        pass

    @abc.abstractmethod
    async def close(self) -> None:
        pass

    @abc.abstractmethod
    async def execute_query(self, query: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        pass


class Neo4jAdapter(GraphStore):
    def __init__(self, uri: str, user: str, password: str, driver: AsyncDriver | None = None):
        self._uri = uri
        self._user = user
        self._password = password
        self._driver: AsyncDriver | None = driver

    async def connect(self) -> None:
        if not self._driver:
            self._driver = AsyncGraphDatabase.driver(self._uri, auth=(self._user, self._password))
            # Verify connectivity
            await self._driver.verify_connectivity()
            logger.info("Connected to Neo4j successfully.")

    async def close(self) -> None:
        if self._driver:
            await self._driver.close()
            self._driver = None
            logger.info("Closed Neo4j connection.")

    async def execute_query(self, query: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        if not self._driver:
            raise RuntimeError("Neo4j adapter is not connected.")
        
        async with self._driver.session() as session:
            result = await session.run(query, parameters or {})
            records = await result.data()
            return records

# Singleton instance to be used across the app
from app.core.config import settings

graph_store: GraphStore = Neo4jAdapter(
    uri=settings.NEO4J_URI,
    user=settings.NEO4J_USER,
    password=settings.NEO4J_PASSWORD
)

class GraphRepository:
    def __init__(self, store: GraphStore):
        self.store = store

    async def project_output_graph(self, workspace_id: UUID, graph: OutputGraph) -> None:
        """
        Projects an OutputGraph into Neo4j.
        Nodes get labels: OutputNode, plus their specific label.
        Provenance properties are serialized to JSON strings.
        """
        await self.store.connect()
        
        # 1. Project Nodes
        nodes_by_label = {}
        for node in graph.nodes:
            nodes_by_label.setdefault(node.label, []).append(node)
            
        for label, nodes in nodes_by_label.items():
            # Sanitize label to prevent injection (though it's internal)
            safe_label = "".join([c for c in label if c.isalnum() or c == "_"])
            query = f"""
            UNWIND $nodes AS n
            MERGE (on:OutputNode {{id: n.id, workspace_id: $workspace_id}})
            SET on:{safe_label}
            SET on += n.props
            WITH on
            MERGE (w:Workspace {{id: $workspace_id}})
            MERGE (on)-[:BELONGS_TO]->(w)
            """
            
            node_params = []
            for node in nodes:
                props = dict(node.properties)
                if node.provenance:
                    props["provenance_derived_from_refs"] = json.dumps([str(u) for u in node.provenance.derived_from_refs])
                    if node.provenance.calculation:
                        props["provenance_calculation"] = node.provenance.calculation
                    if node.provenance.verification_status:
                        props["provenance_verification_status"] = node.provenance.verification_status
                node_params.append({"id": node.id, "props": props})
            
            await self.store.execute_query(query, {"workspace_id": str(workspace_id), "nodes": node_params})
            
        # 2. Project Edges
        edges_by_type = {}
        for edge in graph.edges:
            edges_by_type.setdefault(edge.type, []).append(edge)
            
        for edge_type, edges in edges_by_type.items():
            safe_edge_type = "".join([c for c in edge_type if c.isalnum() or c == "_"])
            query = f"""
            UNWIND $edges AS e
            MATCH (source:OutputNode {{id: e.source_id, workspace_id: $workspace_id}})
            MATCH (target:OutputNode {{id: e.target_id, workspace_id: $workspace_id}})
            MERGE (source)-[rel:{safe_edge_type}]->(target)
            SET rel += e.props
            """
            edge_params = [{"source_id": e.source_id, "target_id": e.target_id, "props": e.properties} for e in edges]
            await self.store.execute_query(query, {"workspace_id": str(workspace_id), "edges": edge_params})

    async def get_output_graph(self, workspace_id: UUID) -> OutputGraph:
        await self.store.connect()
        
        # 1. Get Nodes
        nodes_query = """
        MATCH (on:OutputNode {workspace_id: $workspace_id})
        RETURN on, labels(on) AS labels
        """
        node_records = await self.store.execute_query(nodes_query, {"workspace_id": str(workspace_id)})
        
        graph_nodes = []
        for record in node_records:
            node_dict = record["on"]
            labels = record["labels"]
            label = next((l for l in labels if l != "OutputNode"), "Unknown")
            
            props = dict(node_dict)
            node_id = props.pop("id")
            props.pop("workspace_id", None)
            
            provenance = None
            if "provenance_derived_from_refs" in props:
                refs_json = props.pop("provenance_derived_from_refs")
                refs = [UUID(ref) for ref in json.loads(refs_json)]
                calc = props.pop("provenance_calculation", None)
                status = props.pop("provenance_verification_status", None)
                provenance = ProvenanceBundle(
                    derived_from_refs=refs,
                    calculation=calc,
                    verification_status=status
                )
                
            graph_nodes.append(OutputGraphNode(
                id=node_id,
                label=label,
                properties=props,
                provenance=provenance
            ))
            
        # 2. Get Edges
        edges_query = """
        MATCH (source:OutputNode {workspace_id: $workspace_id})-[rel]->(target:OutputNode {workspace_id: $workspace_id})
        RETURN source.id AS source_id, target.id AS target_id, type(rel) AS edge_type, properties(rel) AS props
        """
        edge_records = await self.store.execute_query(edges_query, {"workspace_id": str(workspace_id)})
        
        graph_edges = []
        for record in edge_records:
            graph_edges.append(OutputGraphEdge(
                source_id=record["source_id"],
                target_id=record["target_id"],
                type=record["edge_type"],
                properties=record["props"]
            ))
            
        return OutputGraph(nodes=graph_nodes, edges=graph_edges)
