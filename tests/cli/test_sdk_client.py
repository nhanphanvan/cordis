import asyncio
from pathlib import Path

import httpx

from cordis.cli.sdk.client import CordisClient


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


def test_request_raises_runtime_error_for_http_failures() -> None:
    response = httpx.Response(
        status_code=404,
        text='{"detail":"missing"}',
        request=httpx.Request("GET", "http://127.0.0.1:8000/api/v1/users/me"),
    )
    transport = FakeHttpxService(response)
    client = CordisClient(base_url="http://127.0.0.1:8000")
    client.transport = transport  # type: ignore[assignment]

    try:
        asyncio.run(client.get_me())
    except RuntimeError as exc:
        assert "missing" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")


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
    monkeypatch.setattr("cordis.cli.sdk.client.copy_from_cache", lambda repo_id, checksum, destination: True)

    result = asyncio.run(
        client.download_version(repository_id=7, version_name="v1", save_dir=str(tmp_path / "downloads"))
    )

    assert result == {"downloaded": ["models/file.bin"]}
