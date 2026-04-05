import asyncio
from pathlib import Path

from fastapi.testclient import TestClient

from cordis.backend.app import create_app
from cordis.backend.config import build_config
from cordis.backend.db.base import ModelBase
from cordis.backend.db.session import get_engine, get_session_factory
from cordis.backend.models import User
from cordis.backend.security.passwords import hash_password


async def _reset_database() -> None:
    engine = get_engine()
    async with engine.begin() as connection:
        await connection.run_sync(ModelBase.metadata.drop_all)
        await connection.run_sync(ModelBase.metadata.create_all)


async def _create_user(*, email: str, password: str, is_active: bool = True, is_admin: bool = False) -> None:
    session_factory = get_session_factory()
    async with session_factory() as session:
        session.add(
            User(
                email=email,
                password_hash=hash_password(password),
                is_active=is_active,
                is_admin=is_admin,
            )
        )
        await session.commit()


def test_login_returns_bearer_token_for_valid_credentials(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "cordis-auth.db"
    monkeypatch.setenv("CORDIS_DB_URL", f"sqlite+aiosqlite:///{db_path}")
    build_config.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    asyncio.run(_reset_database())
    asyncio.run(_create_user(email="admin@example.com", password="password123", is_admin=True))

    client = TestClient(create_app())

    response = client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "password123"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["access_token"]


def test_login_rejects_invalid_credentials(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "cordis-auth-invalid.db"
    monkeypatch.setenv("CORDIS_DB_URL", f"sqlite+aiosqlite:///{db_path}")
    build_config.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    asyncio.run(_reset_database())
    asyncio.run(_create_user(email="user@example.com", password="password123"))

    client = TestClient(create_app())

    response = client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "wrong-password"})

    assert response.status_code == 401
    assert response.json() == {
        "error": {"code": "authentication_error", "message": "Invalid credentials"},
    }


def test_current_user_endpoint_requires_valid_bearer_token(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "cordis-auth-me.db"
    monkeypatch.setenv("CORDIS_DB_URL", f"sqlite+aiosqlite:///{db_path}")
    build_config.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    asyncio.run(_reset_database())
    asyncio.run(_create_user(email="user@example.com", password="password123"))

    client = TestClient(create_app())
    login_response = client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "password123"})
    token = login_response.json()["access_token"]

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == {
        "email": "user@example.com",
        "is_active": True,
        "is_admin": False,
    }

    invalid_response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid-token"})

    assert invalid_response.status_code == 401
    assert invalid_response.json() == {
        "error": {"code": "authentication_error", "message": "Invalid bearer token"},
    }


def test_admin_endpoint_rejects_non_admin_users(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "cordis-auth-admin.db"
    monkeypatch.setenv("CORDIS_DB_URL", f"sqlite+aiosqlite:///{db_path}")
    build_config.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    asyncio.run(_reset_database())
    asyncio.run(_create_user(email="user@example.com", password="password123", is_admin=False))

    client = TestClient(create_app())
    login_response = client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "password123"})
    token = login_response.json()["access_token"]

    response = client.get("/api/v1/auth/admin-check", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403
    assert response.json() == {
        "error": {"code": "authorization_error", "message": "Admin privileges required"},
    }
