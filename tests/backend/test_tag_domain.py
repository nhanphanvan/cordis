import asyncio
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from cordis.backend.app import create_app
from cordis.backend.config import build_config
from cordis.backend.db.base import ModelBase
from cordis.backend.db.session import get_engine, get_session_factory
from cordis.backend.models import Repository, RepositoryMember, Role, User
from cordis.backend.security.passwords import hash_password


async def _reset_database() -> None:
    engine = get_engine()
    async with engine.begin() as connection:
        await connection.run_sync(ModelBase.metadata.drop_all)
        await connection.run_sync(ModelBase.metadata.create_all)


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


async def _create_user(*, email: str, password: str) -> int:
    session_factory = get_session_factory()
    async with session_factory() as session:
        user = User(
            email=email,
            password_hash=hash_password(password),
            is_active=True,
            is_admin=False,
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


def _create_version(client: TestClient, headers: dict[str, str], repository_id: int, name: str) -> str:
    response = client.post(
        "/api/v1/versions",
        json={"repository_id": repository_id, "name": name},
        headers=headers,
    )
    return response.json()["id"]


def test_developer_can_create_get_list_lookup_and_delete_tags(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "cordis-tag-domain.db"
    monkeypatch.setenv("CORDIS_DB_URL", f"sqlite+aiosqlite:///{db_path}")
    build_config.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    asyncio.run(_reset_database())
    asyncio.run(_seed_roles())
    developer_id = asyncio.run(_create_user(email="developer@example.com", password="password123"))
    repository_id = asyncio.run(_create_repository(name="repo-tag"))
    asyncio.run(_add_membership(repository_id=repository_id, user_id=developer_id, role_name="developer"))

    client = TestClient(create_app())
    headers = _auth_header(client, "developer@example.com", "password123")
    version_id = _create_version(client, headers, repository_id, "v1")

    create_response = client.post(
        "/api/v1/tags",
        json={"repository_id": repository_id, "version_id": version_id, "name": "latest"},
        headers=headers,
    )
    tag_id = create_response.json()["id"]

    get_response = client.get(f"/api/v1/tags/{tag_id}", headers=headers)
    lookup_response = client.get(
        "/api/v1/tags",
        params={"repository_id": repository_id, "name": "latest"},
        headers=headers,
    )
    list_response = client.get(f"/api/v1/repositories/{repository_id}/tags", headers=headers)
    delete_response = client.delete(f"/api/v1/tags/{tag_id}", headers=headers)

    expected = {
        "id": tag_id,
        "repository_id": repository_id,
        "name": "latest",
        "version_id": version_id,
        "version_name": "v1",
    }
    assert create_response.status_code == 201
    assert create_response.json() == expected
    assert get_response.status_code == 200
    assert get_response.json() == expected
    assert lookup_response.status_code == 200
    assert lookup_response.json() == expected
    assert list_response.status_code == 200
    assert list_response.json() == {"items": [expected]}
    assert delete_response.status_code == 200
    assert delete_response.json() == expected


def test_tag_name_must_be_unique_within_repository_and_version_must_match_repository(
    monkeypatch,
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "cordis-tag-unique.db"
    monkeypatch.setenv("CORDIS_DB_URL", f"sqlite+aiosqlite:///{db_path}")
    build_config.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    asyncio.run(_reset_database())
    asyncio.run(_seed_roles())
    developer_id = asyncio.run(_create_user(email="developer@example.com", password="password123"))
    repo_a = asyncio.run(_create_repository(name="repo-a"))
    repo_b = asyncio.run(_create_repository(name="repo-b"))
    asyncio.run(_add_membership(repository_id=repo_a, user_id=developer_id, role_name="developer"))
    asyncio.run(_add_membership(repository_id=repo_b, user_id=developer_id, role_name="developer"))

    client = TestClient(create_app())
    headers = _auth_header(client, "developer@example.com", "password123")
    version_a = _create_version(client, headers, repo_a, "v1")
    version_b = _create_version(
        client,
        headers,
        repo_b,
        "v1",
    )

    first_response = client.post(
        "/api/v1/tags",
        json={"repository_id": repo_a, "version_id": version_a, "name": "stable"},
        headers=headers,
    )
    duplicate_same_repo = client.post(
        "/api/v1/tags",
        json={"repository_id": repo_a, "version_id": version_a, "name": "stable"},
        headers=headers,
    )
    wrong_repository_version = client.post(
        "/api/v1/tags",
        json={"repository_id": repo_a, "version_id": version_b, "name": "other"},
        headers=headers,
    )

    assert first_response.status_code == 201
    assert duplicate_same_repo.status_code == 409
    assert duplicate_same_repo.json() == {
        "error": {"code": "conflict", "message": "Tag name already exists in repository"},
    }
    assert wrong_repository_version.status_code == 422
    assert wrong_repository_version.json() == {
        "error": {"code": "validation_error", "message": "Version does not belong to repository"},
    }


def test_viewer_can_read_but_cannot_create_or_delete_tags(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "cordis-tag-rbac.db"
    monkeypatch.setenv("CORDIS_DB_URL", f"sqlite+aiosqlite:///{db_path}")
    build_config.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    asyncio.run(_reset_database())
    asyncio.run(_seed_roles())
    developer_id = asyncio.run(_create_user(email="developer@example.com", password="password123"))
    viewer_id = asyncio.run(_create_user(email="viewer@example.com", password="password123"))
    repository_id = asyncio.run(_create_repository(name="repo-rbac"))
    asyncio.run(_add_membership(repository_id=repository_id, user_id=developer_id, role_name="developer"))
    asyncio.run(_add_membership(repository_id=repository_id, user_id=viewer_id, role_name="viewer"))

    client = TestClient(create_app())
    developer_headers = _auth_header(client, "developer@example.com", "password123")
    viewer_headers = _auth_header(client, "viewer@example.com", "password123")
    version_id = _create_version(client, developer_headers, repository_id, "v1")
    create_response = client.post(
        "/api/v1/tags",
        json={"repository_id": repository_id, "version_id": version_id, "name": "latest"},
        headers=developer_headers,
    )
    tag_id = create_response.json()["id"]

    read_response = client.get(f"/api/v1/tags/{tag_id}", headers=viewer_headers)
    create_denied = client.post(
        "/api/v1/tags",
        json={"repository_id": repository_id, "version_id": version_id, "name": "new"},
        headers=viewer_headers,
    )
    delete_denied = client.delete(f"/api/v1/tags/{tag_id}", headers=viewer_headers)

    assert read_response.status_code == 200
    assert create_denied.status_code == 403
    assert delete_denied.status_code == 403
