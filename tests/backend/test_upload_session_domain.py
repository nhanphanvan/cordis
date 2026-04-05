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


class FakeStorageAdapter:
    def __init__(self) -> None:
        self._next_upload = 1
        self.parts: dict[str, dict[int, str]] = {}
        self.completed_etag = "sha256:complete"
        self.aborted: list[str] = []

    def create_multipart_upload(self, ref) -> str:
        upload_id = f"upload-{self._next_upload}"
        self._next_upload += 1
        self.parts[upload_id] = {}
        return upload_id

    def upload_part(self, ref, *, upload_id: str, part_number: int, body: bytes):
        _ = ref
        _ = body
        etag = f"etag-{part_number}"
        self.parts[upload_id][part_number] = etag
        return type("UploadedPart", (), {"part_number": part_number, "etag": etag})()

    def complete_multipart_upload(self, ref, *, upload_id: str, parts):
        _ = ref
        _ = upload_id
        _ = parts
        return type("CompletedMultipartUpload", (), {"etag": self.completed_etag, "version_id": "object-v1"})()

    def abort_multipart_upload(self, ref, *, upload_id: str) -> None:
        _ = ref
        self.aborted.append(upload_id)


def test_developer_can_create_resume_and_complete_upload_session(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "cordis-upload-session.db"
    monkeypatch.setenv("CORDIS_DB_URL", f"sqlite+aiosqlite:///{db_path}")
    build_config.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    asyncio.run(_reset_database())
    asyncio.run(_seed_roles())
    developer_id = asyncio.run(_create_user(email="developer@example.com", password="password123"))
    repository_id = asyncio.run(_create_repository(name="repo-uploads"))
    asyncio.run(_add_membership(repository_id=repository_id, user_id=developer_id, role_name="developer"))

    fake_storage = FakeStorageAdapter()
    fake_storage.completed_etag = "sha256:upload-ok"
    monkeypatch.setattr(
        "cordis.backend.services.upload.storage_factory.get_storage_adapter",
        lambda: fake_storage,
    )

    client = TestClient(create_app())
    headers = _auth_header(client, "developer@example.com", "password123")
    version_id = _create_version(client, headers, repository_id, "v1")

    create_response = client.post(
        "/api/v1/uploads/sessions",
        json={
            "version_id": version_id,
            "path": "models/upload.bin",
            "checksum": "sha256:upload-ok",
            "size": 11,
        },
        headers=headers,
    )
    session_id = create_response.json()["id"]
    resumed_response = client.post(
        "/api/v1/uploads/sessions",
        json={
            "version_id": version_id,
            "path": "models/upload.bin",
            "checksum": "sha256:upload-ok",
            "size": 11,
        },
        headers=headers,
    )
    upload_response = client.post(
        f"/api/v1/uploads/sessions/{session_id}/parts",
        json={"part_number": 1, "content": "hello world"},
        headers=headers,
    )
    get_response = client.get(f"/api/v1/uploads/sessions/{session_id}", headers=headers)
    complete_response = client.post(f"/api/v1/uploads/sessions/{session_id}/complete", headers=headers)
    version_artifacts_response = client.get(f"/api/v1/versions/{version_id}/artifacts", headers=headers)

    assert create_response.status_code == 201
    assert create_response.json()["status"] == "created"
    assert resumed_response.status_code == 200
    assert resumed_response.json()["id"] == session_id
    assert upload_response.status_code == 200
    assert upload_response.json()["status"] == "in_progress"
    assert upload_response.json()["parts"] == [{"part_number": 1, "etag": "etag-1"}]
    assert get_response.status_code == 200
    assert get_response.json()["parts"] == [{"part_number": 1, "etag": "etag-1"}]
    assert complete_response.status_code == 200
    assert complete_response.json()["status"] == "completed"
    assert complete_response.json()["artifact_id"] is not None
    assert version_artifacts_response.status_code == 200
    assert version_artifacts_response.json() == {
        "items": [
            {
                "id": complete_response.json()["artifact_id"],
                "repository_id": repository_id,
                "path": "models/upload.bin",
                "name": "upload.bin",
                "checksum": "sha256:upload-ok",
                "size": 11,
            }
        ]
    }


def test_checksum_mismatch_marks_session_failed_without_version_artifact(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "cordis-upload-session-failed.db"
    monkeypatch.setenv("CORDIS_DB_URL", f"sqlite+aiosqlite:///{db_path}")
    build_config.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    asyncio.run(_reset_database())
    asyncio.run(_seed_roles())
    developer_id = asyncio.run(_create_user(email="developer@example.com", password="password123"))
    repository_id = asyncio.run(_create_repository(name="repo-upload-failed"))
    asyncio.run(_add_membership(repository_id=repository_id, user_id=developer_id, role_name="developer"))

    fake_storage = FakeStorageAdapter()
    fake_storage.completed_etag = "sha256:wrong"
    monkeypatch.setattr(
        "cordis.backend.services.upload.storage_factory.get_storage_adapter",
        lambda: fake_storage,
    )

    client = TestClient(create_app())
    headers = _auth_header(client, "developer@example.com", "password123")
    version_id = _create_version(client, headers, repository_id, "v1")
    create_response = client.post(
        "/api/v1/uploads/sessions",
        json={
            "version_id": version_id,
            "path": "models/bad.bin",
            "checksum": "sha256:expected",
            "size": 3,
        },
        headers=headers,
    )
    session_id = create_response.json()["id"]
    client.post(
        f"/api/v1/uploads/sessions/{session_id}/parts",
        json={"part_number": 1, "content": "bad"},
        headers=headers,
    )

    complete_response = client.post(f"/api/v1/uploads/sessions/{session_id}/complete", headers=headers)
    get_response = client.get(f"/api/v1/uploads/sessions/{session_id}", headers=headers)
    version_artifacts_response = client.get(f"/api/v1/versions/{version_id}/artifacts", headers=headers)

    assert complete_response.status_code == 409
    assert complete_response.json()["error"]["code"] == "conflict"
    assert get_response.status_code == 200
    assert get_response.json()["status"] == "failed"
    assert version_artifacts_response.status_code == 200
    assert version_artifacts_response.json() == {"items": []}


def test_developer_can_abort_upload_session(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "cordis-upload-session-abort.db"
    monkeypatch.setenv("CORDIS_DB_URL", f"sqlite+aiosqlite:///{db_path}")
    build_config.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    asyncio.run(_reset_database())
    asyncio.run(_seed_roles())
    developer_id = asyncio.run(_create_user(email="developer@example.com", password="password123"))
    repository_id = asyncio.run(_create_repository(name="repo-upload-abort"))
    asyncio.run(_add_membership(repository_id=repository_id, user_id=developer_id, role_name="developer"))

    fake_storage = FakeStorageAdapter()
    monkeypatch.setattr(
        "cordis.backend.services.upload.storage_factory.get_storage_adapter",
        lambda: fake_storage,
    )

    client = TestClient(create_app())
    headers = _auth_header(client, "developer@example.com", "password123")
    version_id = _create_version(client, headers, repository_id, "v1")
    create_response = client.post(
        "/api/v1/uploads/sessions",
        json={
            "version_id": version_id,
            "path": "models/abort.bin",
            "checksum": "sha256:abort",
            "size": 5,
        },
        headers=headers,
    )
    session_id = create_response.json()["id"]

    abort_response = client.post(f"/api/v1/uploads/sessions/{session_id}/abort", headers=headers)
    get_response = client.get(f"/api/v1/uploads/sessions/{session_id}", headers=headers)

    assert abort_response.status_code == 200
    assert abort_response.json()["status"] == "aborted"
    assert get_response.status_code == 200
    assert get_response.json()["status"] == "aborted"
    assert fake_storage.aborted == [create_response.json()["upload_id"]]
