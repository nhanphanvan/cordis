import asyncio
import base64
from pathlib import Path

import httpx

from cordis.cli.errors import ApiError, TransportError
from cordis.cli.sdk.client import CordisClient
from cordis.cli.transfer.constants import DEFAULT_TRANSFER_CHUNK_SIZE


class FakeHttpxService:
    def __init__(self, response: httpx.Response) -> None:
        self.response = response
        self.calls: list[tuple[str, str, dict[str, object]]] = []

    async def request(self, method: str, path: str, **kwargs: object) -> httpx.Response:
        self.calls.append((method, path, kwargs))
        return self.response


def test_login_uses_httpx_transport_and_authorization_headers() -> None:
    response = httpx.Response(
        status_code=200,
        json={"access_token": "token-123"},
        request=httpx.Request("POST", "http://127.0.0.1:8000/api/v1/auth/login"),
    )
    transport = FakeHttpxService(response)
    client = CordisClient(base_url="http://127.0.0.1:8000", token="secret-token")
    client.transport = transport  # type: ignore[assignment]

    token = asyncio.run(client.login(email="user@example.com", password="password123"))

    assert token == "token-123"
    assert transport.calls == [
        (
            "POST",
            "/api/v1/auth/login",
            {
                "json": {"email": "user@example.com", "password": "password123"},
                "headers": {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer secret-token",
                },
            },
        )
    ]


def test_request_raises_api_error_for_http_failures() -> None:
    response = httpx.Response(
        status_code=404,
        json={
            "status_code": 404,
            "app_status_code": 1400,
            "message": "Version not found",
            "detail": "Version v1 not found",
        },
        request=httpx.Request("GET", "http://127.0.0.1:8000/api/v1/users/me"),
    )
    transport = FakeHttpxService(response)
    client = CordisClient(base_url="http://127.0.0.1:8000")
    client.transport = transport  # type: ignore[assignment]

    try:
        asyncio.run(client.get_me())
    except ApiError as exc:
        assert exc.http_status == 404
        assert exc.app_status_code == 1400
        assert exc.status_message == "Version not found"
        assert exc.user_message == "Version v1 not found"
    else:
        raise AssertionError("expected ApiError")


def test_request_raises_transport_error_for_connect_failures() -> None:
    class FailingHttpxService:
        async def request(self, method: str, path: str, **kwargs: object) -> httpx.Response:
            raise httpx.ConnectError(
                "connection refused", request=httpx.Request(method, f"http://127.0.0.1:8000{path}")
            )

    client = CordisClient(base_url="http://127.0.0.1:8000")
    client.transport = FailingHttpxService()  # type: ignore[assignment]

    try:
        asyncio.run(client.get_me())
    except TransportError as exc:
        assert "Could not connect" in exc.user_message
        assert "TRANSPORT" in exc.status_line
    else:
        raise AssertionError("expected TransportError")


def test_client_exposes_domain_apis_and_facade_methods_delegate() -> None:
    client = CordisClient(base_url="http://127.0.0.1:8000")

    assert hasattr(client, "auth")
    assert hasattr(client, "users")
    assert hasattr(client, "repositories")
    assert hasattr(client, "versions")
    assert hasattr(client, "tags")
    assert hasattr(client, "transfers")

    async def fake_login(*, email: str, password: str) -> str:
        assert email == "user@example.com"
        assert password == "password123"
        return "token-from-auth-api"

    client.auth.login = fake_login  # type: ignore[method-assign]

    token = asyncio.run(client.login(email="user@example.com", password="password123"))

    assert token == "token-from-auth-api"


def test_download_version_uses_cached_file_before_remote_download(
    monkeypatch,
    tmp_path: Path,
) -> None:
    client = CordisClient(base_url="http://127.0.0.1:8000")

    async def fake_list_version_artifacts(self, *, repository_id: int, version_name: str) -> list[dict[str, object]]:
        assert repository_id == 7
        assert version_name == "v1"
        return [{"path": "models/file.bin", "checksum": "sha256:file", "size": 10}]

    async def fake_download_item(
        self,
        *,
        repository_id: int,
        version_name: str,
        path: str,
        save_path: str,
    ) -> dict[str, object]:
        raise AssertionError(f"download_item should not be called for cached artifact: {path} -> {save_path}")

    monkeypatch.setattr(CordisClient, "list_version_artifacts", fake_list_version_artifacts)
    monkeypatch.setattr(CordisClient, "download_item", fake_download_item)
    monkeypatch.setattr("cordis.cli.sdk.transfers.copy_from_cache", lambda repo_id, checksum, destination: True)

    result = asyncio.run(
        client.download_version(repository_id=7, version_name="v1", save_dir=str(tmp_path / "downloads"))
    )

    assert result == {"downloaded": ["models/file.bin"]}


def test_download_version_uses_transport_stream_download_for_remote_file(
    monkeypatch,
    tmp_path: Path,
) -> None:
    client = CordisClient(base_url="http://127.0.0.1:8000")
    streamed: list[tuple[str, Path]] = []
    cached: list[tuple[str, str, Path]] = []

    class FakeTransport:
        def stream_download(self, *, path: str, save_path: Path, show_progress: bool = True) -> None:
            assert show_progress is True
            streamed.append((path, save_path))
            save_path.parent.mkdir(parents=True, exist_ok=True)
            save_path.write_bytes(b"payload")

    async def fake_list_version_artifacts(self, *, repository_id: int, version_name: str) -> list[dict[str, object]]:
        assert repository_id == 7
        assert version_name == "v1"
        return [{"path": "models/file.bin", "checksum": "sha256:file", "size": 7}]

    async def fake_download_item(
        self,
        *,
        repository_id: int,
        version_name: str,
        path: str,
        save_path: str,
    ) -> dict[str, object]:
        assert repository_id == 7
        assert version_name == "v1"
        assert path == "models/file.bin"
        assert save_path.endswith("models/file.bin")
        return {"download_url": "https://example.com/download/file.bin"}

    monkeypatch.setattr(CordisClient, "list_version_artifacts", fake_list_version_artifacts)
    monkeypatch.setattr(CordisClient, "download_item", fake_download_item)
    monkeypatch.setattr("cordis.cli.sdk.transfers.copy_from_cache", lambda repo_id, checksum, destination: False)
    monkeypatch.setattr(
        "cordis.cli.sdk.transfers.save_to_cache",
        lambda repository_key, checksum, source_path: cached.append((repository_key, checksum, source_path)),
    )
    client.transport = FakeTransport()  # type: ignore[assignment]

    result = asyncio.run(
        client.download_version(repository_id=7, version_name="v1", save_dir=str(tmp_path / "downloads"))
    )

    destination = tmp_path / "downloads" / "models" / "file.bin"
    assert result == {"downloaded": ["models/file.bin"]}
    assert streamed == [("https://example.com/download/file.bin", destination)]
    assert cached == [("7", "sha256:file", destination)]
    assert destination.read_bytes() == b"payload"


def test_upload_directory_skips_files_ignored_by_cordisignore(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / "payloads"
    root.mkdir()
    (root / ".cordisignore").write_text("*.tmp\n", encoding="utf-8")
    (root / "keep.txt").write_text("keep", encoding="utf-8")
    (root / "ignore.tmp").write_text("ignore", encoding="utf-8")

    client = CordisClient(base_url="http://127.0.0.1:8000")
    requests: list[tuple[str, str, dict[str, object] | None]] = []

    async def fake_get_version(self, *, repository_id: int, name: str) -> dict[str, object]:
        assert repository_id == 7
        assert name == "v1"
        return {"id": "version-1", "name": "v1"}

    async def fake_request(
        self,
        *,
        method: str,
        path: str,
        payload: dict[str, object] | None = None,
    ) -> dict[str, object]:
        requests.append((method, path, payload))
        if path == "/api/v1/uploads/sessions":
            return {"id": "session-1"}
        return {}

    monkeypatch.setattr(CordisClient, "get_version", fake_get_version)
    monkeypatch.setattr(CordisClient, "request", fake_request)
    monkeypatch.setattr("cordis.cli.sdk.transfers.save_to_cache", lambda repository_key, checksum, source_path: None)

    result = asyncio.run(
        client.upload_directory(
            repository_id=7,
            version_name="v1",
            folder_path=str(root),
        )
    )

    assert result == {"uploaded": ["keep.txt"], "reused": []}
    assert requests[0] == (
        "POST",
        "/api/v1/resources/check",
        {
            "version_id": "version-1",
            "path": "keep.txt",
            "checksum": "sha256:6ca7ea2feefc88ecb5ed6356ed963f47dc9137f82526fdd25d618ea626d0803f",
            "size": 4,
        },
    )
    assert requests[1] == (
        "POST",
        "/api/v1/uploads/sessions",
        {
            "version_id": "version-1",
            "path": "keep.txt",
            "checksum": "sha256:6ca7ea2feefc88ecb5ed6356ed963f47dc9137f82526fdd25d618ea626d0803f",
            "size": 4,
        },
    )


def test_upload_directory_splits_large_file_into_multiple_parts(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / "payloads"
    root.mkdir()
    payload = b"a" * DEFAULT_TRANSFER_CHUNK_SIZE + b"b" * 5
    (root / "large.bin").write_bytes(payload)

    client = CordisClient(base_url="http://127.0.0.1:8000")
    requests: list[tuple[str, str, dict[str, object] | None]] = []

    async def fake_get_version(self, *, repository_id: int, name: str) -> dict[str, object]:
        assert repository_id == 7
        assert name == "v1"
        return {"id": "version-1", "name": "v1"}

    async def fake_request(
        self,
        *,
        method: str,
        path: str,
        payload: dict[str, object] | None = None,
    ) -> dict[str, object]:
        requests.append((method, path, payload))
        if path == "/api/v1/uploads/sessions":
            return {"id": "session-1", "parts": []}
        return {}

    monkeypatch.setattr(CordisClient, "get_version", fake_get_version)
    monkeypatch.setattr(CordisClient, "request", fake_request)
    monkeypatch.setattr("cordis.cli.sdk.transfers.save_to_cache", lambda repository_key, checksum, source_path: None)

    result = asyncio.run(
        client.upload_directory(
            repository_id=7,
            version_name="v1",
            folder_path=str(root),
        )
    )

    assert result == {"uploaded": ["large.bin"], "reused": []}
    assert requests[0][1] == "/api/v1/resources/check"
    assert requests[2:4] == [
        (
            "POST",
            "/api/v1/uploads/sessions/session-1/parts",
            {
                "part_number": 1,
                "content_base64": base64.b64encode(b"a" * DEFAULT_TRANSFER_CHUNK_SIZE).decode("ascii"),
            },
        ),
        (
            "POST",
            "/api/v1/uploads/sessions/session-1/parts",
            {
                "part_number": 2,
                "content_base64": base64.b64encode(b"b" * 5).decode("ascii"),
            },
        ),
    ]
    assert requests[4] == ("POST", "/api/v1/uploads/sessions/session-1/complete", None)


def test_upload_directory_resumes_by_skipping_existing_uploaded_parts(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / "payloads"
    root.mkdir()
    payload = b"a" * DEFAULT_TRANSFER_CHUNK_SIZE + b"b" * 7
    (root / "resume.bin").write_bytes(payload)

    client = CordisClient(base_url="http://127.0.0.1:8000")
    requests: list[tuple[str, str, dict[str, object] | None]] = []

    async def fake_get_version(self, *, repository_id: int, name: str) -> dict[str, object]:
        return {"id": "version-1", "name": name}

    async def fake_request(
        self,
        *,
        method: str,
        path: str,
        payload: dict[str, object] | None = None,
    ) -> dict[str, object]:
        requests.append((method, path, payload))
        if path == "/api/v1/uploads/sessions":
            return {"id": "session-1", "parts": [{"part_number": 1, "etag": "etag-1"}]}
        return {}

    monkeypatch.setattr(CordisClient, "get_version", fake_get_version)
    monkeypatch.setattr(CordisClient, "request", fake_request)
    monkeypatch.setattr("cordis.cli.sdk.transfers.save_to_cache", lambda repository_key, checksum, source_path: None)

    result = asyncio.run(
        client.upload_directory(
            repository_id=7,
            version_name="v1",
            folder_path=str(root),
        )
    )

    assert result == {"uploaded": ["resume.bin"], "reused": []}
    assert requests[0][1] == "/api/v1/resources/check"
    assert requests[2:3] == [
        (
            "POST",
            "/api/v1/uploads/sessions/session-1/parts",
            {
                "part_number": 2,
                "content_base64": base64.b64encode(b"b" * 7).decode("ascii"),
            },
        )
    ]
    assert requests[3] == ("POST", "/api/v1/uploads/sessions/session-1/complete", None)


def test_upload_directory_reuses_matching_repository_artifact_without_upload(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / "payloads"
    root.mkdir()
    (root / "keep.txt").write_text("keep", encoding="utf-8")

    client = CordisClient(base_url="http://127.0.0.1:8000")
    requests: list[tuple[str, str, dict[str, object] | None]] = []

    async def fake_get_version(self, *, repository_id: int, name: str) -> dict[str, object]:
        assert repository_id == 7
        assert name == "v1"
        return {"id": "version-1", "name": "v1"}

    async def fake_request(
        self,
        *,
        method: str,
        path: str,
        payload: dict[str, object] | None = None,
    ) -> dict[str, object]:
        requests.append((method, path, payload))
        if path == "/api/v1/resources/check":
            return {"status": "exists", "artifact_id": "artifact-1"}
        if path == "/api/v1/versions/version-1/artifacts":
            return {"id": "artifact-1"}
        raise AssertionError(f"unexpected request: {method} {path}")

    monkeypatch.setattr(CordisClient, "get_version", fake_get_version)
    monkeypatch.setattr(CordisClient, "request", fake_request)

    result = asyncio.run(
        client.upload_directory(
            repository_id=7,
            version_name="v1",
            folder_path=str(root),
        )
    )

    assert result == {"uploaded": [], "reused": ["keep.txt"]}
    assert requests == [
        (
            "POST",
            "/api/v1/resources/check",
            {
                "version_id": "version-1",
                "path": "keep.txt",
                "checksum": "sha256:6ca7ea2feefc88ecb5ed6356ed963f47dc9137f82526fdd25d618ea626d0803f",
                "size": 4,
            },
        ),
        (
            "POST",
            "/api/v1/versions/version-1/artifacts",
            {"artifact_id": "artifact-1"},
        ),
    ]
