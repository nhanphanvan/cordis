import asyncio
import logging

from fastapi.testclient import TestClient

from cordis.backend.__main__ import main
from cordis.backend.api.errors import cordis_error_handler
from cordis.backend.app import create_app
from cordis.backend.errors import AuthenticationError


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


def test_backend_main_configures_logging_before_running_server(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    monkeypatch.setattr(
        "cordis.backend.__main__.build_config",
        lambda: type(
            "FakeConfig",
            (),
            {"app": type("FakeAppConfig", (), {"host": "127.0.0.1", "port": 9000, "log_level": "DEBUG"})()},
        )(),
    )
    monkeypatch.setattr(
        "cordis.backend.__main__.setup_logging",
        lambda *, log_level: calls.append(("setup_logging", log_level)),
    )
    monkeypatch.setattr(
        "cordis.backend.__main__.uvicorn.run",
        lambda app, host, port: calls.append(("uvicorn.run", (host, port))),
    )

    main()

    assert calls == [
        ("setup_logging", "DEBUG"),
        ("uvicorn.run", ("127.0.0.1", 9000)),
    ]


def test_cordis_error_handler_logs_exception(caplog) -> None:
    caplog.set_level(logging.ERROR)

    async def call_handler():
        return await cordis_error_handler(
            None,
            AuthenticationError("Invalid credentials"),
        )

    response = asyncio.run(call_handler())

    assert response.status_code == 401
    assert any(
        "Invalid credentials" in message and "authentication_error" in message for message in caplog.messages
    )
