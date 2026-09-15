from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_200():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_root_returns_200():
    response = client.get("/")
    assert response.status_code == 200
    assert "health" in response.json()


def test_health_not_found_on_wrong_path():
    response = client.get("/health")
    assert response.status_code == 404
