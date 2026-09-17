from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import AsyncMock, patch, MagicMock

client = TestClient(app)

def test_health_check():
    mock_engine = MagicMock()
    mock_conn = AsyncMock()
    mock_engine.connect.return_value.__aenter__.return_value = mock_conn
    
    with patch("app.main.engine", mock_engine):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        mock_conn.execute.assert_called_once()
        
        mock_conn.execute.side_effect = Exception("DB down")
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json() == {"status": "degraded"}

