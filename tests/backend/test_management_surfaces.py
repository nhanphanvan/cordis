import asyncio
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from cordis.backend.app import create_app
from cordis.backend.config import build_config
from cordis.backend.database import get_engine, get_session_factory
from cordis.backend.models import Repository, RepositoryMember, Role, User
from cordis.backend.models.base import DatabaseModel
from cordis.backend.security.passwords import hash_password, verify_password


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


async def _create_repository(*, name: str) -> int:
    session_factory = get_session_factory()
    async with session_factory() as session:
        repository = Repository(name=name, description=name, is_public=False)
        session.add(repository)
        await session.commit()
        await session.refresh(repository)
        return repository.id


async def _add_membership(*, repository_id: int, user_id: int, role_name: str) -> None:
    session_factory = get_session_factory()
    async with session_factory() as session:
        role = await session.scalar(select(Role).where(Role.name == role_name))
        if role is None:
            raise AssertionError(f"missing role {role_name}")
        session.add(RepositoryMember(repository_id=repository_id, user_id=user_id, role_id=role.id))
        await session.commit()


def _auth_header(client: TestClient, email: str, password: str) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_user_self_service_and_repository_listing(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "cordis-user-surfaces.db"
    monkeypatch.setenv("CORDIS_DB_URL", f"sqlite+aiosqlite:///{db_path}")
    build_config.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    asyncio.run(_reset_database())
    asyncio.run(_seed_roles())
    user_id = asyncio.run(_create_user(email="user@example.com", password="password123"))
    repository_id = asyncio.run(_create_repository(name="repo-user"))
    asyncio.run(_add_membership(repository_id=repository_id, user_id=user_id, role_name="developer"))

    client = TestClient(create_app())
    headers = _auth_header(client, "user@example.com", "password123")

    me_response = client.get("/api/v1/users/me", headers=headers)
    update_response = client.patch(
        "/api/v1/users/me",
        json={"email": "user+updated@example.com"},
        headers=headers,
    )
    repositories_response = client.get("/api/v1/users/me/repositories", headers=headers)

    assert me_response.status_code == 200
    assert me_response.json() == {
        "id": user_id,
        "email": "user@example.com",
        "is_active": True,
        "is_admin": False,
    }
    assert update_response.status_code == 200
    assert update_response.json()["email"] == "user+updated@example.com"
    assert repositories_response.status_code == 200
    assert repositories_response.json() == {
        "items": [
            {
                "repository_id": repository_id,
                "repository_name": "repo-user",
                "role_name": "developer",
            }
        ]
    }


def test_admin_can_manage_users(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "cordis-admin-users.db"
    monkeypatch.setenv("CORDIS_DB_URL", f"sqlite+aiosqlite:///{db_path}")
    build_config.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    asyncio.run(_reset_database())
    asyncio.run(_seed_roles())
    admin_id = asyncio.run(_create_user(email="admin@example.com", password="password123", is_admin=True))
    user_id = asyncio.run(_create_user(email="existing@example.com", password="password123"))

    client = TestClient(create_app())
    admin_headers = _auth_header(client, "admin@example.com", "password123")

    list_response = client.get("/api/v1/admin/users", headers=admin_headers)
    get_response = client.get(f"/api/v1/users/{user_id}", headers=admin_headers)
    get_by_email_response = client.get("/api/v1/users/emails/existing@example.com", headers=admin_headers)
    create_response = client.post(
        "/api/v1/admin/users",
        json={
            "email": "new@example.com",
            "password": "password456",
            "is_active": True,
            "is_admin": False,
        },
        headers=admin_headers,
    )
    created_id = create_response.json()["id"]
    update_response = client.patch(
        f"/api/v1/admin/users/{created_id}",
        json={"is_admin": True},
        headers=admin_headers,
    )
    delete_response = client.delete(f"/api/v1/admin/users/{created_id}", headers=admin_headers)

    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["id"] == admin_id
    assert get_response.status_code == 200
    assert get_response.json()["id"] == user_id
    assert get_by_email_response.status_code == 200
    assert get_by_email_response.json()["email"] == "existing@example.com"
    assert create_response.status_code == 201
    assert create_response.json()["email"] == "new@example.com"
    assert update_response.status_code == 200
    assert update_response.json()["is_admin"] is True
    assert delete_response.status_code == 200
    assert delete_response.json()["id"] == created_id

    async def _assert_deleted() -> None:
        session_factory = get_session_factory()
        async with session_factory() as session:
            deleted = await session.get(User, created_id)
            assert deleted is None

    asyncio.run(_assert_deleted())


def test_admin_can_manage_roles(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "cordis-admin-roles.db"
    monkeypatch.setenv("CORDIS_DB_URL", f"sqlite+aiosqlite:///{db_path}")
    build_config.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    asyncio.run(_reset_database())
    asyncio.run(_seed_roles())
    asyncio.run(_create_user(email="admin@example.com", password="password123", is_admin=True))

    client = TestClient(create_app())
    admin_headers = _auth_header(client, "admin@example.com", "password123")

    list_response = client.get("/api/v1/roles", headers=admin_headers)
    create_response = client.post(
        "/api/v1/admin/roles",
        json={"name": "tester", "description": "test role"},
        headers=admin_headers,
    )
    role_id = create_response.json()["id"]
    get_response = client.get(f"/api/v1/roles/{role_id}", headers=admin_headers)
    update_response = client.patch(
        f"/api/v1/admin/roles/{role_id}",
        json={"description": "updated role"},
        headers=admin_headers,
    )
    delete_response = client.delete(f"/api/v1/admin/roles/{role_id}", headers=admin_headers)

    assert list_response.status_code == 200
    assert {item["name"] for item in list_response.json()["items"]} == {"owner", "developer", "viewer"}
    assert create_response.status_code == 201
    assert create_response.json()["name"] == "tester"
    assert get_response.status_code == 200
    assert get_response.json()["id"] == role_id
    assert update_response.status_code == 200
    assert update_response.json()["description"] == "updated role"
    assert delete_response.status_code == 200
    assert delete_response.json()["id"] == role_id


def test_admin_user_creation_hashes_password(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "cordis-admin-user-password.db"
    monkeypatch.setenv("CORDIS_DB_URL", f"sqlite+aiosqlite:///{db_path}")
    build_config.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    asyncio.run(_reset_database())
    asyncio.run(_seed_roles())
    asyncio.run(_create_user(email="admin@example.com", password="password123", is_admin=True))

    client = TestClient(create_app())
    admin_headers = _auth_header(client, "admin@example.com", "password123")
    create_response = client.post(
        "/api/v1/admin/users",
        json={
            "email": "hashed@example.com",
            "password": "secret789",
            "is_active": True,
            "is_admin": False,
        },
        headers=admin_headers,
    )
    created_id = create_response.json()["id"]

    async def _assert_password_hash() -> None:
        session_factory = get_session_factory()
        async with session_factory() as session:
            user = await session.get(User, created_id)
            assert user is not None
            assert user.password_hash != "secret789"
            assert verify_password("secret789", user.password_hash)

    asyncio.run(_assert_password_hash())
