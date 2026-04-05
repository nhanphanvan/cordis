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


async def _create_user(*, email: str, password: str) -> int:
    session_factory = get_session_factory()
    async with session_factory() as session:
        user = User(
            email=email,
            password_hash=get_password_hash(password),
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


def test_developer_can_register_artifact_associate_it_with_version_and_list_version_artifacts(
    monkeypatch,
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "cordis-artifact-domain.db"
    monkeypatch.setenv("CORDIS_DB_URL", f"sqlite+aiosqlite:///{db_path}")
    build_config.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    asyncio.run(_reset_database())
    asyncio.run(_seed_roles())
    developer_id = asyncio.run(_create_user(email="developer@example.com", password="password123"))
    repository_id = asyncio.run(_create_repository(name="repo-artifacts"))
    asyncio.run(_add_membership(repository_id=repository_id, user_id=developer_id, role_name="developer"))

    client = TestClient(create_app())
    headers = _auth_header(client, "developer@example.com", "password123")
    version_id = _create_version(client, headers, repository_id, "v1")

    register_response = client.post(
        "/api/v1/artifacts",
        json={
            "repository_id": repository_id,
            "path": "models/weights.bin",
            "checksum": "sha256:abc123",
            "size": 1024,
        },
        headers=headers,
    )
    artifact_id = register_response.json()["id"]

    attach_response = client.post(
        f"/api/v1/versions/{version_id}/artifacts",
        json={"artifact_id": artifact_id},
        headers=headers,
    )
    get_response = client.get(f"/api/v1/artifacts/{artifact_id}", headers=headers)
    list_response = client.get(f"/api/v1/versions/{version_id}/artifacts", headers=headers)

    expected = {
        "id": artifact_id,
        "repository_id": repository_id,
        "path": "models/weights.bin",
        "name": "weights.bin",
        "checksum": "sha256:abc123",
        "size": 1024,
    }
    assert register_response.status_code == 201
    assert register_response.json() == expected
    assert attach_response.status_code == 201
    assert attach_response.json() == expected
    assert get_response.status_code == 200
    assert get_response.json() == expected
    assert list_response.status_code == 200
    assert list_response.json() == {"items": [expected]}


def test_resource_check_distinguishes_match_conflict_and_missing(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "cordis-resource-check.db"
    monkeypatch.setenv("CORDIS_DB_URL", f"sqlite+aiosqlite:///{db_path}")
    build_config.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    asyncio.run(_reset_database())
    asyncio.run(_seed_roles())
    developer_id = asyncio.run(_create_user(email="developer@example.com", password="password123"))
    repository_id = asyncio.run(_create_repository(name="repo-check"))
    asyncio.run(_add_membership(repository_id=repository_id, user_id=developer_id, role_name="developer"))

    client = TestClient(create_app())
    headers = _auth_header(client, "developer@example.com", "password123")
    version_id = _create_version(client, headers, repository_id, "v1")
    artifact_response = client.post(
        "/api/v1/artifacts",
        json={
            "repository_id": repository_id,
            "path": "models/model.bin",
            "checksum": "sha256:same",
            "size": 256,
        },
        headers=headers,
    )
    artifact_id = artifact_response.json()["id"]
    client.post(
        f"/api/v1/versions/{version_id}/artifacts",
        json={"artifact_id": artifact_id},
        headers=headers,
    )

    exact_response = client.post(
        "/api/v1/resources/check",
        json={
            "version_id": version_id,
            "path": "models/model.bin",
            "checksum": "sha256:same",
            "size": 256,
        },
        headers=headers,
    )
    conflict_response = client.post(
        "/api/v1/resources/check",
        json={
            "version_id": version_id,
            "path": "models/model.bin",
            "checksum": "sha256:different",
            "size": 999,
        },
        headers=headers,
    )
    missing_response = client.post(
        "/api/v1/resources/check",
        json={
            "version_id": version_id,
            "path": "models/new.bin",
            "checksum": "sha256:new",
            "size": 512,
        },
        headers=headers,
    )

    assert exact_response.status_code == 200
    assert exact_response.json() == {"status": "exists", "artifact_id": artifact_id}
    assert conflict_response.status_code == 200
    assert conflict_response.json() == {"status": "conflict", "artifact_id": artifact_id}
    assert missing_response.status_code == 200
    assert missing_response.json() == {"status": "missing", "artifact_id": None}


def test_viewer_can_read_artifacts_but_cannot_register_or_attach(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "cordis-artifact-rbac.db"
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
    artifact_response = client.post(
        "/api/v1/artifacts",
        json={
            "repository_id": repository_id,
            "path": "assets/readme.txt",
            "checksum": "sha256:viewer",
            "size": 64,
        },
        headers=developer_headers,
    )
    artifact_id = artifact_response.json()["id"]
    client.post(
        f"/api/v1/versions/{version_id}/artifacts",
        json={"artifact_id": artifact_id},
        headers=developer_headers,
    )

    read_response = client.get(f"/api/v1/artifacts/{artifact_id}", headers=viewer_headers)
    register_denied = client.post(
        "/api/v1/artifacts",
        json={
            "repository_id": repository_id,
            "path": "assets/new.txt",
            "checksum": "sha256:new",
            "size": 12,
        },
        headers=viewer_headers,
    )
    attach_denied = client.post(
        f"/api/v1/versions/{version_id}/artifacts",
        json={"artifact_id": artifact_id},
        headers=viewer_headers,
    )

    assert read_response.status_code == 200
    assert register_denied.status_code == 403
    assert attach_denied.status_code == 403
