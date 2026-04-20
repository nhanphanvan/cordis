import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from cordis.backend.__main__ import main
from cordis.backend.app import create_app
from cordis.backend.exceptions import AppStatus, UnauthorizedError, configure_exception_handlers
from cordis.backend.exceptions.exception_handlers import _custom_unauthorized_error_handler


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
        "cordis.backend.__main__.setup",
        lambda: calls.append(("setup", None)),
    )
    monkeypatch.setattr(
        "cordis.backend.__main__.uvicorn.run",
        lambda app, host, port: calls.append(("uvicorn.run", (host, port))),
    )

    main()

    assert calls == [
        ("setup", None),
        ("uvicorn.run", ("127.0.0.1", 9000)),
    ]


def test_backend_settings_setup_builds_config_and_configures_logging(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []
    fake_config = type(
        "FakeConfig",
        (),
        {
            "app": type("FakeAppConfig", (), {"log_level": "WARNING"})(),
            "security": type(
                "FakeSecurityConfig",
                (),
                {"secret_key": "secret-key", "jwt_algorithm": "HS256", "access_token_expire_minutes": 90},
            )(),
        },
    )()

    monkeypatch.setattr("cordis.backend.settings.build_config", lambda: fake_config)
    monkeypatch.setattr(
        "cordis.backend.settings.setup_logging",
        lambda *, log_level: calls.append(("setup_logging", log_level)),
    )
    monkeypatch.setattr(
        "cordis.backend.settings.setup_security",
        lambda **kwargs: calls.append(("setup_security", kwargs)),
    )

    from cordis.backend.settings import setup

    setup()

    assert calls == [
        ("setup_logging", "WARNING"),
        (
            "setup_security",
            {
                "secret_key": "secret-key",
                "jwt_algorithm": "HS256",
                "access_token_expire_minutes": 90,
            },
        ),
    ]


def test_create_app_bootstraps_runtime_state_on_startup(monkeypatch) -> None:
    calls: list[str] = []

    async def _fake_bootstrap() -> None:
        calls.append("bootstrap")

    monkeypatch.setattr("cordis.backend.app.bootstrap_runtime_state", _fake_bootstrap, raising=False)

    with TestClient(create_app()) as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    assert calls == ["bootstrap"]


def test_cordis_error_handler_logs_exception(caplog) -> None:
    caplog.set_level(logging.ERROR)
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/auth-error",
        "headers": [],
        "query_string": b"",
        "scheme": "http",
        "server": ("testserver", 80),
        "client": ("testclient", 50000),
        "root_path": "",
    }
    from starlette.requests import Request

    response = _custom_unauthorized_error_handler(
        Request(scope),
        UnauthorizedError("Invalid credentials", app_status=AppStatus.ERROR_INVALID_CREDENTIALS),
    )

    assert response.status_code == 401
    assert any("Invalid credentials" in message and "1001" in message for message in caplog.messages)


def test_backend_errors_use_app_status_payload() -> None:
    app = FastAPI()
    configure_exception_handlers(app)

    @app.get("/auth-error")
    async def auth_error() -> dict[str, str]:
        raise UnauthorizedError("Invalid credentials", app_status=AppStatus.ERROR_INVALID_CREDENTIALS)

    client = TestClient(app)

    response = client.get("/auth-error")

    assert response.status_code == 401
    assert response.json() == {
        "status_code": 401,
        "app_status_code": 1001,
        "message": "Invalid credentials",
        "detail": "Invalid credentials",
    }


def test_request_validation_errors_are_normalized() -> None:
    app = FastAPI()
    configure_exception_handlers(app)

    @app.get("/typed")
    async def typed(limit: int) -> dict[str, int]:
        return {"limit": limit}

    client = TestClient(app)

    response = client.get("/typed", params={"limit": "oops"})

    assert response.status_code == 422
    assert response.json()["status_code"] == 422
    assert response.json()["app_status_code"] == 1000
    assert response.json()["message"] == "Validation error"
    assert isinstance(response.json()["detail"], list)


def test_unhandled_exceptions_are_normalized() -> None:
    app = FastAPI()
    configure_exception_handlers(app)

    @app.get("/boom")
    async def boom() -> dict[str, str]:
        raise RuntimeError("boom")

    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/boom")

    assert response.status_code == 500
    assert response.json() == {
        "status_code": 500,
        "app_status_code": 500,
        "message": "Internal server error",
        "detail": "boom",
    }
