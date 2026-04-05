import asyncio
from pathlib import Path

from fastapi.testclient import TestClient

from cordis.backend.app import create_app
from cordis.backend.config import build_config
from cordis.backend.database import get_engine, get_session_factory
from cordis.backend.models import Role, User
from cordis.backend.models.base import DatabaseModel
from cordis.backend.security.passwords import hash_password


async def _reset_database() -> None:
    engine = get_engine()
    async with engine.begin() as connection:
        await connection.run_sync(DatabaseModel.metadata.drop_all)
        await connection.run_sync(DatabaseModel.metadata.create_all)


async def _seed_roles() -> None:
    session_factory = get_session_factory()
    async with session_factory() as session:
        session.add_all(
            [
                Role(name="owner", description="full repository control"),
                Role(name="developer", description="mutation access"),
                Role(name="viewer", description="read access"),
            ]
        )
        await session.commit()


async def _create_user(*, email: str, password: str, is_admin: bool = False) -> int:
    session_factory = get_session_factory()
    async with session_factory() as session:
        user = User(
            email=email,
            password_hash=hash_password(password),
            is_active=True,
            is_admin=is_admin,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user.id


def _auth_header(client: TestClient, email: str, password: str) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_admin_can_create_list_update_and_delete_repository(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "cordis-repository-domain.db"
    monkeypatch.setenv("CORDIS_DB_URL", f"sqlite+aiosqlite:///{db_path}")
    build_config.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    asyncio.run(_reset_database())
    asyncio.run(_seed_roles())
    asyncio.run(_create_user(email="admin@example.com", password="password123", is_admin=True))

    client = TestClient(create_app())
    headers = _auth_header(client, "admin@example.com", "password123")

    create_response = client.post(
        "/api/v1/repositories",
        json={"name": "repo-alpha", "description": "alpha", "is_public": False},
        headers=headers,
    )
    repository_id = create_response.json()["id"]

    list_response = client.get("/api/v1/repositories", headers=headers)
    get_response = client.get(f"/api/v1/repositories/{repository_id}", headers=headers)
    update_response = client.patch(
        f"/api/v1/repositories/{repository_id}",
        json={"description": "renamed", "is_public": True},
        headers=headers,
    )
    delete_response = client.delete(f"/api/v1/repositories/{repository_id}", headers=headers)

    assert create_response.status_code == 201
    assert create_response.json() == {
        "id": repository_id,
        "name": "repo-alpha",
        "description": "alpha",
        "is_public": False,
    }
    assert list_response.status_code == 200
    assert list_response.json() == {
        "items": [
            {
                "id": repository_id,
                "name": "repo-alpha",
                "description": "alpha",
                "is_public": False,
            }
        ]
    }
    assert get_response.status_code == 200
    assert update_response.status_code == 200
    assert update_response.json() == {
        "id": repository_id,
        "name": "repo-alpha",
        "description": "renamed",
        "is_public": True,
    }
    assert delete_response.status_code == 200
    assert delete_response.json()["id"] == repository_id


def test_owner_can_manage_repository_members(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "cordis-repository-members.db"
    monkeypatch.setenv("CORDIS_DB_URL", f"sqlite+aiosqlite:///{db_path}")
    build_config.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    asyncio.run(_reset_database())
    asyncio.run(_seed_roles())
    asyncio.run(_create_user(email="admin@example.com", password="password123", is_admin=True))
    invited_user_id = asyncio.run(_create_user(email="guest@example.com", password="password123"))

    client = TestClient(create_app())
    admin_headers = _auth_header(client, "admin@example.com", "password123")
    create_response = client.post(
        "/api/v1/repositories",
        json={"name": "repo-members", "description": "members", "is_public": False},
        headers=admin_headers,
    )
    repository_id = create_response.json()["id"]

    add_response = client.post(
        f"/api/v1/repositories/{repository_id}/members",
        json={"user_id": invited_user_id, "role": "developer"},
        headers=admin_headers,
    )
    list_response = client.get(f"/api/v1/repositories/{repository_id}/members", headers=admin_headers)
    update_response = client.patch(
        f"/api/v1/repositories/{repository_id}/members/{invited_user_id}",
        json={"role": "viewer"},
        headers=admin_headers,
    )
    remove_response = client.delete(
        f"/api/v1/repositories/{repository_id}/members/{invited_user_id}",
        headers=admin_headers,
    )

    assert add_response.status_code == 201
    assert add_response.json() == {"email": "guest@example.com", "role": "developer"}
    assert list_response.status_code == 200
    assert list_response.json() == {
        "items": [
            {"email": "admin@example.com", "role": "owner"},
            {"email": "guest@example.com", "role": "developer"},
        ]
    }
    assert update_response.status_code == 200
    assert update_response.json() == {"email": "guest@example.com", "role": "viewer"}
    assert remove_response.status_code == 200
    assert remove_response.json() == {"email": "guest@example.com", "role": "viewer"}


def test_non_admin_cannot_create_repository(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "cordis-repository-create-denied.db"
    monkeypatch.setenv("CORDIS_DB_URL", f"sqlite+aiosqlite:///{db_path}")
    build_config.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    asyncio.run(_reset_database())
    asyncio.run(_seed_roles())
    asyncio.run(_create_user(email="user@example.com", password="password123"))

    client = TestClient(create_app())
    headers = _auth_header(client, "user@example.com", "password123")

    response = client.post(
        "/api/v1/repositories",
        json={"name": "repo-denied", "description": "denied", "is_public": False},
        headers=headers,
    )

    assert response.status_code == 403
    assert response.json() == {
        "error": {"code": "authorization_error", "message": "Admin privileges required"},
    }
