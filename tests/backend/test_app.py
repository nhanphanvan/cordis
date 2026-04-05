from fastapi.testclient import TestClient

from cordis.backend.app import create_app


def test_health_endpoint_reports_service_status() -> None:
    client = TestClient(create_app())

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"service": "cordis-backend", "status": "ok"}


def test_version_endpoint_reports_project_version() -> None:
    client = TestClient(create_app())

    response = client.get("/version")

    assert response.status_code == 200
    assert response.json() == {"name": "cordis", "version": "0.1.0"}


def test_versioned_api_router_is_mounted() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
