import asyncio
from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select

from cordis.backend.app import create_app
from cordis.backend.config import build_config
from cordis.backend.database import get_engine, get_session_factory
from cordis.backend.enums import RepositoryVisibility
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


async def _create_repository(
    *,
    name: str,
    visibility: RepositoryVisibility = RepositoryVisibility.PRIVATE,
) -> int:
    session_factory = get_session_factory()
    async with session_factory() as session:
        repository = Repository(name=name, description=name, visibility=visibility.value)
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


def _create_artifact(client: TestClient, headers: dict[str, str], repository_id: int, path: str) -> str:
    response = client.post(
        "/api/v1/artifacts",
        json={
            "repository_id": repository_id,
            "path": path,
            "checksum": "sha256:artifact",
            "size": 128,
            "storage_version_id": "object-v1",
        },
        headers=headers,
    )
    return response.json()["id"]


class FakeDownloadStorage:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str, int]] = []

    def get_download_url(self, ref, *, expires_in: int) -> str:
        self.calls.append((ref.artifact_id, ref.path, ref.repository_id, expires_in))
        return f"https://download.invalid/{ref.repository_id}/{ref.artifact_id}?expires={expires_in}"


def test_viewer_can_lookup_version_artifact_by_path_and_request_download(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "cordis-download-domain.db"
    monkeypatch.setenv("CORDIS_DB_URL", f"sqlite+aiosqlite:///{db_path}")
    build_config.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    asyncio.run(_reset_database())
    asyncio.run(_seed_roles())
    developer_id = asyncio.run(_create_user(email="developer@example.com", password="password123"))
    viewer_id = asyncio.run(_create_user(email="viewer@example.com", password="password123"))
    repository_id = asyncio.run(_create_repository(name="repo-downloads"))
    asyncio.run(_add_membership(repository_id=repository_id, user_id=developer_id, role_name="developer"))
    asyncio.run(_add_membership(repository_id=repository_id, user_id=viewer_id, role_name="viewer"))

    fake_storage = FakeDownloadStorage()
    monkeypatch.setattr(
        "cordis.backend.services.download.storage_factory.get_storage_adapter",
        lambda: fake_storage,
    )

    client = TestClient(create_app())
    developer_headers = _auth_header(client, "developer@example.com", "password123")
    viewer_headers = _auth_header(client, "viewer@example.com", "password123")
    version_id = _create_version(client, developer_headers, repository_id, "v1")
    artifact_id = _create_artifact(client, developer_headers, repository_id, "models/weights.bin")
    client.post(
        f"/api/v1/versions/{version_id}/artifacts",
        json={"artifact_id": artifact_id},
        headers=developer_headers,
    )

    lookup_response = client.get(
        f"/api/v1/versions/{version_id}/artifacts/by-path",
        params={"path": "models/weights.bin"},
        headers=viewer_headers,
    )
    download_response = client.post(
        f"/api/v1/versions/{version_id}/artifacts/{artifact_id}/download",
        headers=viewer_headers,
    )

    assert lookup_response.status_code == 200
    assert lookup_response.json() == {
        "id": artifact_id,
        "repository_id": repository_id,
        "path": "models/weights.bin",
        "name": "weights.bin",
        "checksum": "sha256:artifact",
        "size": 128,
        "storage_version_id": "object-v1",
        "public_url": None,
    }
    assert download_response.status_code == 200
    assert download_response.json() == {
        "artifact_id": artifact_id,
        "download_url": f"https://download.invalid/{repository_id}/{artifact_id}?expires=3600",
        "expires_in": 3600,
    }
    assert fake_storage.calls == [(UUID(artifact_id), "models/weights.bin", repository_id, 3600)]


def test_logged_in_non_member_can_download_from_authenticated_repository(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "cordis-download-authenticated.db"
    monkeypatch.setenv("CORDIS_DB_URL", f"sqlite+aiosqlite:///{db_path}")
    build_config.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    asyncio.run(_reset_database())
    asyncio.run(_seed_roles())
    developer_id = asyncio.run(_create_user(email="developer@example.com", password="password123"))
    asyncio.run(_create_user(email="reader@example.com", password="password123"))
    repository_id = asyncio.run(
        _create_repository(name="repo-authenticated-downloads", visibility=RepositoryVisibility.AUTHENTICATED)
    )
    asyncio.run(_add_membership(repository_id=repository_id, user_id=developer_id, role_name="developer"))

    fake_storage = FakeDownloadStorage()
    monkeypatch.setattr(
        "cordis.backend.services.download.storage_factory.get_storage_adapter",
        lambda: fake_storage,
    )

    client = TestClient(create_app())
    developer_headers = _auth_header(client, "developer@example.com", "password123")
    reader_headers = _auth_header(client, "reader@example.com", "password123")
    version_id = _create_version(client, developer_headers, repository_id, "v1")
    artifact_id = _create_artifact(client, developer_headers, repository_id, "public/model.bin")
    client.post(
        f"/api/v1/versions/{version_id}/artifacts",
        json={"artifact_id": artifact_id},
        headers=developer_headers,
    )

    lookup_response = client.get(
        f"/api/v1/versions/{version_id}/artifacts/by-path",
        params={"path": "public/model.bin"},
        headers=reader_headers,
    )
    download_response = client.post(
        f"/api/v1/versions/{version_id}/artifacts/{artifact_id}/download",
        headers=reader_headers,
    )

    assert lookup_response.status_code == 200
    assert lookup_response.json()["id"] == artifact_id
    assert download_response.status_code == 200
    assert download_response.json()["artifact_id"] == artifact_id


def test_download_is_rejected_for_artifact_not_in_version(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "cordis-download-invalid-artifact.db"
    monkeypatch.setenv("CORDIS_DB_URL", f"sqlite+aiosqlite:///{db_path}")
    build_config.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    asyncio.run(_reset_database())
    asyncio.run(_seed_roles())
    developer_id = asyncio.run(_create_user(email="developer@example.com", password="password123"))
    viewer_id = asyncio.run(_create_user(email="viewer@example.com", password="password123"))
    repository_id = asyncio.run(_create_repository(name="repo-download-invalid"))
    asyncio.run(_add_membership(repository_id=repository_id, user_id=developer_id, role_name="developer"))
    asyncio.run(_add_membership(repository_id=repository_id, user_id=viewer_id, role_name="viewer"))

    fake_storage = FakeDownloadStorage()
    monkeypatch.setattr(
        "cordis.backend.services.download.storage_factory.get_storage_adapter",
        lambda: fake_storage,
    )

    client = TestClient(create_app())
    developer_headers = _auth_header(client, "developer@example.com", "password123")
    viewer_headers = _auth_header(client, "viewer@example.com", "password123")
    version_id = _create_version(client, developer_headers, repository_id, "v1")
    artifact_id = _create_artifact(client, developer_headers, repository_id, "models/unattached.bin")

    download_response = client.post(
        f"/api/v1/versions/{version_id}/artifacts/{artifact_id}/download",
        headers=viewer_headers,
    )

    assert download_response.status_code == 404
    assert download_response.json()["app_status_code"] == 1600
    assert fake_storage.calls == []
