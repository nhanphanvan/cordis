from pathlib import Path

import httpx

from cordis.cli.utils.files import iter_file_chunks, iter_files
from cordis.constants import DEFAULT_TRANSFER_CHUNK_SIZE
from cordis.sdk.httpx_service import HttpxService


def test_iter_files_skips_paths_ignored_by_cordisignore(tmp_path: Path) -> None:
    root = tmp_path / "payloads"
    root.mkdir()
    (root / ".cordisignore").write_text("*.tmp\nbuild/\n", encoding="utf-8")
    (root / "keep.txt").write_text("keep", encoding="utf-8")
    (root / "ignore.tmp").write_text("ignore", encoding="utf-8")
    build_dir = root / "build"
    build_dir.mkdir()
    (build_dir / "artifact.bin").write_text("bin", encoding="utf-8")

    items = list(iter_files(root))

    assert items == [(root / "keep.txt", "keep.txt")]


def test_iter_files_supports_gitignore_style_negation(tmp_path: Path) -> None:
    root = tmp_path / "payloads"
    root.mkdir()
    (root / ".cordisignore").write_text("*.txt\n!important.txt\n", encoding="utf-8")
    (root / "drop.txt").write_text("drop", encoding="utf-8")
    (root / "important.txt").write_text("keep", encoding="utf-8")

    items = list(iter_files(root))

    assert items == [(root / "important.txt", "important.txt")]


def test_iter_files_skips_cordis_metadata_by_default(tmp_path: Path) -> None:
    root = tmp_path / "payloads"
    root.mkdir()
    (root / ".cordisignore").write_text("", encoding="utf-8")
    metadata_dir = root / ".cordis"
    metadata_dir.mkdir()
    (metadata_dir / "config.json").write_text("{}", encoding="utf-8")
    (root / "keep.txt").write_text("keep", encoding="utf-8")

    items = list(iter_files(root))

    assert items == [(root / "keep.txt", "keep.txt")]


def test_iter_file_chunks_splits_file_using_default_transfer_chunk_size(tmp_path: Path) -> None:
    payload = b"a" * DEFAULT_TRANSFER_CHUNK_SIZE + b"b" * 3
    path = tmp_path / "artifact.bin"
    path.write_bytes(payload)

    chunks = list(iter_file_chunks(path))

    assert chunks == [
        (1, b"a" * DEFAULT_TRANSFER_CHUNK_SIZE),
        (2, b"bbb"),
    ]


class _FakeStreamResponse:
    def __init__(
        self,
        *,
        status_code: int,
        chunks: list[bytes | Exception],
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self._chunks = chunks
        self.headers = headers or {}

    def __enter__(self) -> "_FakeStreamResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def iter_bytes(self, chunk_size: int) -> object:
        del chunk_size
        for chunk in self._chunks:
            if isinstance(chunk, Exception):
                raise chunk
            yield chunk


def test_stream_download_resumes_after_remote_protocol_error(monkeypatch, tmp_path: Path) -> None:
    calls: list[dict[str, object]] = []
    responses = [
        _FakeStreamResponse(
            status_code=200,
            chunks=[b"abc", httpx.RemoteProtocolError("stream interrupted")],
            headers={"Content-Length": "10"},
        ),
        _FakeStreamResponse(
            status_code=206,
            chunks=[b"defghij"],
            headers={"Content-Length": "7"},
        ),
    ]

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            del args, kwargs

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

        def stream(self, method: str, url: str, headers: dict[str, str] | None = None):
            calls.append({"method": method, "url": url, "headers": headers})
            return responses.pop(0)

    monkeypatch.setattr("cordis.sdk.httpx_service.httpx.Client", FakeClient)
    destination = tmp_path / "artifact.bin"

    HttpxService().stream_download(path="https://example.com/artifact.bin", save_path=destination, show_progress=False)

    assert destination.read_bytes() == b"abcdefghij"
    assert calls == [
        {"method": "GET", "url": "https://example.com/artifact.bin", "headers": None},
        {"method": "GET", "url": "https://example.com/artifact.bin", "headers": {"Range": "bytes=3-"}},
    ]


def test_stream_download_restarts_when_server_ignores_resume_range(monkeypatch, tmp_path: Path) -> None:
    calls: list[dict[str, object]] = []
    destination = tmp_path / "artifact.bin"
    destination.write_bytes(b"abc")
    responses = [
        _FakeStreamResponse(
            status_code=200,
            chunks=[b"abcdefghij"],
            headers={"Content-Length": "10"},
        )
    ]

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            del args, kwargs

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

        def stream(self, method: str, url: str, headers: dict[str, str] | None = None):
            calls.append({"method": method, "url": url, "headers": headers})
            return responses.pop(0)

    monkeypatch.setattr("cordis.sdk.httpx_service.httpx.Client", FakeClient)

    HttpxService().stream_download(path="https://example.com/artifact.bin", save_path=destination, show_progress=False)

    assert destination.read_bytes() == b"abcdefghij"
    assert calls == [{"method": "GET", "url": "https://example.com/artifact.bin", "headers": {"Range": "bytes=3-"}}]


def test_stream_download_updates_progress_when_enabled(monkeypatch, tmp_path: Path) -> None:
    progress_events: list[tuple[str, object, object]] = []

    class FakeProgress:
        def __enter__(self) -> "FakeProgress":
            progress_events.append(("enter", None, None))
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            progress_events.append(("exit", None, None))
            return False

        def add_task(self, description: str, *, total: object = None, completed: object = 0) -> int:
            progress_events.append((description, total, completed))
            return 1

        def update(self, task_id: int, *, total: object = None, completed: object | None = None) -> None:
            progress_events.append((f"update:{task_id}", total, completed))

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            del args, kwargs

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

        def stream(self, method: str, url: str, headers: dict[str, str] | None = None):
            del method, url, headers
            return _FakeStreamResponse(
                status_code=200,
                chunks=[b"ab", b"cde"],
                headers={"Content-Length": "5"},
            )

    monkeypatch.setattr("cordis.sdk.httpx_service.httpx.Client", FakeClient)
    monkeypatch.setattr("cordis.sdk.httpx_service.HttpxService._create_download_progress", lambda self: FakeProgress())

    destination = tmp_path / "artifact.bin"

    HttpxService().stream_download(path="https://example.com/artifact.bin", save_path=destination, show_progress=True)

    assert destination.read_bytes() == b"abcde"
    assert progress_events == [
        ("enter", None, None),
        ("Downloading artifact.bin", 5, 0),
        ("update:1", 5, 2),
        ("update:1", 5, 5),
        ("exit", None, None),
    ]
