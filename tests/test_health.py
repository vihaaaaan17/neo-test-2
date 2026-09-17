from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import AsyncMock, patch, MagicMock

client = TestClient(app)

def test_health_check():
    mock_engine = MagicMock()
    mock_conn = AsyncMock()
    mock_engine.connect.return_value.__aenter__.return_value = mock_conn
    
    mock_graph = AsyncMock()

    with patch("app.main.engine", mock_engine), \
         patch("app.main.graph_store", mock_graph):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "postgres": "ok", "neo4j": "ok"}
        mock_conn.execute.assert_called_once()
        mock_graph.execute_query.assert_called_once_with("RETURN 1")
        
        mock_conn.execute.side_effect = Exception("DB down")
        mock_graph.execute_query.side_effect = Exception("Neo4j down")
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json() == {"status": "degraded", "postgres": "failed", "neo4j": "failed"}

