import pytest
from unittest.mock import patch, MagicMock

def test_health_endpoint(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"ok": True}

def test_get_food_image_not_found(client):
    res = client.get("/api/food-image/NON_EXISTENT")
    assert res.status_code == 404
    assert "detail" in res.json()

def test_get_food_image_found_but_missing_file(client):
    with patch("app.AsyncSessionLocal") as mock_session_local:
        mock_session = mock_session_local.return_value.__aenter__.return_value
        mock_execute = mock_session.execute
        
        mock_result = MagicMock()
        mock_result.scalar.return_value = "south_asia/non_existent.jpg"
        mock_execute.return_value = mock_result
        
        res = client.get("/api/food-image/FOOD_1")
        assert res.status_code == 404
        assert "Image file missing" in res.json()["detail"]
