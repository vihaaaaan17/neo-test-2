import abc
import logging
from typing import Any
from neo4j import AsyncGraphDatabase, AsyncDriver

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
    def __init__(self, uri: str, user: str, password: str):
        self._uri = uri
        self._user = user
        self._password = password
        self._driver: AsyncDriver | None = None

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
