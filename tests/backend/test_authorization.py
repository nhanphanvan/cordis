import asyncio
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from cordis.backend.app import create_app
from cordis.backend.config import build_config
from cordis.backend.database import get_engine, get_session_factory
from cordis.backend.models import Repository, RepositoryMember, Role, User
from cordis.backend.models.base import DatabaseModel
from cordis.backend.security import get_password_hash


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
            password_hash=get_password_hash(password),
            is_active=True,
            is_admin=is_admin,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user.id


async def _create_repository(*, name: str, is_public: bool) -> int:
    session_factory = get_session_factory()
    async with session_factory() as session:
        repository = Repository(name=name, description=f"{name} repo", is_public=is_public)
        session.add(repository)
        await session.commit()
        await session.refresh(repository)
        return repository.id


async def _add_membership(*, repository_id: int, user_id: int, role_name: str) -> None:
    session_factory = get_session_factory()
    async with session_factory() as session:
        role = await session.scalar(select(Role).where(Role.name == role_name))
        if role is None:
            raise AssertionError(f"role {role_name} missing")
        membership = RepositoryMember(repository_id=repository_id, user_id=user_id, role_id=role.id)
        session.add(membership)
        await session.commit()


def _auth_header(client: TestClient, email: str, password: str) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_public_repository_allows_viewer_check_without_membership(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "cordis-rbac-public.db"
    monkeypatch.setenv("CORDIS_DB_URL", f"sqlite+aiosqlite:///{db_path}")
    build_config.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    asyncio.run(_reset_database())
    asyncio.run(_seed_roles())
    repository_id = asyncio.run(_create_repository(name="public-repo", is_public=True))

    client = TestClient(create_app())

    response = client.get(f"/api/v1/repositories/{repository_id}/auth-check/viewer")

    assert response.status_code == 200
    assert response.json() == {"repository_id": repository_id, "access": "viewer"}


def test_private_repository_requires_membership_for_viewer_access(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "cordis-rbac-private.db"
    monkeypatch.setenv("CORDIS_DB_URL", f"sqlite+aiosqlite:///{db_path}")
    build_config.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    asyncio.run(_reset_database())
    asyncio.run(_seed_roles())
    repository_id = asyncio.run(_create_repository(name="private-repo", is_public=False))
    viewer_id = asyncio.run(_create_user(email="viewer@example.com", password="password123"))
    asyncio.run(_add_membership(repository_id=repository_id, user_id=viewer_id, role_name="viewer"))

    client = TestClient(create_app())

    denied_response = client.get(f"/api/v1/repositories/{repository_id}/auth-check/viewer")
    allowed_response = client.get(
        f"/api/v1/repositories/{repository_id}/auth-check/viewer",
        headers=_auth_header(client, "viewer@example.com", "password123"),
    )

    assert denied_response.status_code == 401
    assert allowed_response.status_code == 200
    assert allowed_response.json() == {"repository_id": repository_id, "access": "viewer"}


def test_developer_access_requires_developer_or_owner_or_admin(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "cordis-rbac-developer.db"
    monkeypatch.setenv("CORDIS_DB_URL", f"sqlite+aiosqlite:///{db_path}")
    build_config.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    asyncio.run(_reset_database())
    asyncio.run(_seed_roles())
    repository_id = asyncio.run(_create_repository(name="dev-repo", is_public=False))
    viewer_id = asyncio.run(_create_user(email="viewer@example.com", password="password123"))
    developer_id = asyncio.run(_create_user(email="developer@example.com", password="password123"))
    asyncio.run(_create_user(email="admin@example.com", password="password123", is_admin=True))
    asyncio.run(_add_membership(repository_id=repository_id, user_id=viewer_id, role_name="viewer"))
    asyncio.run(_add_membership(repository_id=repository_id, user_id=developer_id, role_name="developer"))

    client = TestClient(create_app())

    viewer_response = client.get(
        f"/api/v1/repositories/{repository_id}/auth-check/developer",
        headers=_auth_header(client, "viewer@example.com", "password123"),
    )
    developer_response = client.get(
        f"/api/v1/repositories/{repository_id}/auth-check/developer",
        headers=_auth_header(client, "developer@example.com", "password123"),
    )
    admin_response = client.get(
        f"/api/v1/repositories/{repository_id}/auth-check/developer",
        headers=_auth_header(client, "admin@example.com", "password123"),
    )

    assert viewer_response.status_code == 403
    assert developer_response.status_code == 200
    assert admin_response.status_code == 200


def test_membership_listing_requires_owner_or_admin(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "cordis-rbac-members.db"
    monkeypatch.setenv("CORDIS_DB_URL", f"sqlite+aiosqlite:///{db_path}")
    build_config.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    asyncio.run(_reset_database())
    asyncio.run(_seed_roles())
    repository_id = asyncio.run(_create_repository(name="member-repo", is_public=False))
    owner_id = asyncio.run(_create_user(email="owner@example.com", password="password123"))
    developer_id = asyncio.run(_create_user(email="developer@example.com", password="password123"))
    asyncio.run(_add_membership(repository_id=repository_id, user_id=owner_id, role_name="owner"))
    asyncio.run(_add_membership(repository_id=repository_id, user_id=developer_id, role_name="developer"))

    client = TestClient(create_app())

    developer_response = client.get(
        f"/api/v1/repositories/{repository_id}/members",
        headers=_auth_header(client, "developer@example.com", "password123"),
    )
    owner_response = client.get(
        f"/api/v1/repositories/{repository_id}/members",
        headers=_auth_header(client, "owner@example.com", "password123"),
    )

    assert developer_response.status_code == 403
    assert owner_response.status_code == 200
    assert owner_response.json() == {
        "items": [
            {"email": "owner@example.com", "role": "owner"},
            {"email": "developer@example.com", "role": "developer"},
        ]
    }
