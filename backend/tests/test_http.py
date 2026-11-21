from fastapi.testclient import TestClient

from maratoncito.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_status_reports_unimplemented_capabilities() -> None:
    response = client.get("/api/v1/system/status")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Maratoncito"
    assert body["status"] == "scaffold"
    assert not any(body["capabilities"].values())


def test_openapi_publishes_contract() -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert "/api/v1/system/status" in response.json()["paths"]


def test_web_shell() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Maratoncito" in response.text
