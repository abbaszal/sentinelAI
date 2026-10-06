from fastapi.testclient import TestClient

from apps.api.main import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/v1/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"
    assert data["service"] == "SentinelAI"