from pathlib import Path

import httpx

from cordis.cli.transfer.files import iter_files
from cordis.cli.utils.httpx_service import HttpxService


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

    monkeypatch.setattr("cordis.cli.utils.httpx_service.httpx.Client", FakeClient)
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

    monkeypatch.setattr("cordis.cli.utils.httpx_service.httpx.Client", FakeClient)

    HttpxService().stream_download(path="https://example.com/artifact.bin", save_path=destination, show_progress=False)

    assert destination.read_bytes() == b"abcdefghij"
    assert calls == [{"method": "GET", "url": "https://example.com/artifact.bin", "headers": {"Range": "bytes=3-"}}]
