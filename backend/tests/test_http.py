from fastapi.testclient import TestClient

from maratoncito.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_status_does_not_claim_unimplemented_features() -> None:
    response = client.get("/api/v1/system/status")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Maratoncito"
    assert body["status"] == "p1-development"
    assert body["capabilities"]["selection"] is True
    for name in ("library", "automation", "requests", "subtitles"):
        assert body["capabilities"][name] is False


def test_openapi_publishes_contract() -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    assert "/api/v1/system/status" in spec["paths"]
    assert "/api/v1/catalog/search" in spec["paths"]
    assert "/api/v1/releases/search" in spec["paths"]
    assert "/api/v1/downloads" in spec["paths"]


def test_web_shell() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Maratoncito" in response.text
    assert "catalog-form" in response.text
