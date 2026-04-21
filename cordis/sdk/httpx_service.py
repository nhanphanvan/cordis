from collections.abc import Awaitable, Callable
from contextlib import nullcontext
from pathlib import Path
from typing import Any, cast

import httpx
from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TaskID,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from tenacity import RetryError, retry, retry_if_exception_type, retry_if_result, stop_after_attempt, wait_exponential

from cordis.constants import DEFAULT_TRANSFER_CHUNK_SIZE

RETRYABLE_STATUS_CODES = {429, 502, 503, 504}


def is_retryable_status_code(response: httpx.Response | None) -> bool:
    if response is None:
        return True
    return response.status_code in RETRYABLE_STATUS_CODES


class HttpxService:
    def __init__(
        self,
        base_url: str = "",
        retries: int = 3,
        timeout: int | None = 60,
        headers: dict[str, Any] | None = None,
        verify: bool = True,
        **kwargs: Any,
    ) -> None:
        self.base_url: str = base_url
        self.headers: dict[str, Any] | None = headers
        self.retries: int = retries
        self.timeout: int | None = timeout
        self.verify: bool = verify
        self.config: dict[str, Any] = kwargs

    def set_timeout(self, timeout: int | None) -> None:
        self.timeout = timeout

    def _get_retry(self) -> Any:
        retry_argument = (
            retry_if_exception_type(httpx.TimeoutException)
            | retry_if_exception_type(httpx.ConnectError)
            | retry_if_exception_type(httpx.StreamError)
            | retry_if_result(is_retryable_status_code)
        )
        return retry(
            reraise=True,
            retry=retry_argument,
            stop=stop_after_attempt(self.retries),
            wait=wait_exponential(multiplier=1, max=120),
        )

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        kwargs = {**self.config, **kwargs}
        request_headers = httpx.Headers(self.headers, encoding="utf-8") if self.headers is not None else httpx.Headers()
        if "headers" in kwargs:
            request_headers.update(httpx.Headers(kwargs["headers"], encoding="utf-8"))
        kwargs["headers"] = request_headers

        timeout = httpx.Timeout(self.timeout)
        async with httpx.AsyncClient(base_url=self.base_url, timeout=timeout, verify=self.verify) as client:
            return await client.request(method=method, url=path, **kwargs)

    async def _request_with_retry(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        try:
            request_func = cast(
                Callable[..., Awaitable[httpx.Response]],
                self._get_retry()(self._request),
            )
            return await request_func(method, path, **kwargs)
        except RetryError as error:
            last_result = error.last_attempt.result()
            if isinstance(last_result, httpx.Response):
                return last_result
            raise error

    async def request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        return await self._request_with_retry(method, path, **kwargs)

    def _build_client_headers(self, headers: dict[str, str] | None = None) -> dict[str, str] | None:
        request_headers = dict(self.headers or {})
        if headers:
            request_headers.update(headers)
        return request_headers or None

    def _create_download_progress(self) -> Progress:
        return Progress(
            TextColumn("{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=Console(color_system=None, force_terminal=False, highlight=False, soft_wrap=True),
            transient=False,
        )

    @staticmethod
    def _resolve_total_size(
        response: httpx.Response,
        *,
        downloaded_size: int,
        known_total_size: int | None,
    ) -> int | None:
        if known_total_size is not None:
            return known_total_size

        content_range = response.headers.get("Content-Range")
        if content_range and "/" in content_range:
            total = content_range.rsplit("/", maxsplit=1)[-1]
            if total.isdigit():
                return int(total)

        content_length = response.headers.get("Content-Length")
        if content_length and content_length.isdigit():
            return downloaded_size + int(content_length) if response.status_code == 206 else int(content_length)

        return None

    def _stream_download(
        self,
        *,
        path: str,
        save_path: Path,
        chunk_size: int = DEFAULT_TRANSFER_CHUNK_SIZE,
        show_progress: bool = False,
        on_chunk_downloaded: Callable[[int], None] | None = None,
    ) -> httpx.Response:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        downloaded_size = save_path.stat().st_size if save_path.exists() else 0
        known_total_size: int | None = None
        last_response: httpx.Response | None = None
        progress = self._create_download_progress() if show_progress else None
        task_id: TaskID | None = None

        timeout = httpx.Timeout(self.timeout)
        progress_context = progress if progress is not None else nullcontext()
        with progress_context as active_progress:
            with httpx.Client(base_url=self.base_url, timeout=timeout, verify=self.verify, **self.config) as client:
                for _ in range(max(self.retries, 1) + 2):
                    headers = {"Range": f"bytes={downloaded_size}-"} if downloaded_size > 0 else None
                    try:
                        with client.stream("GET", path, headers=self._build_client_headers(headers)) as response:
                            last_response = response
                            if response.status_code in RETRYABLE_STATUS_CODES:
                                return response
                            if response.status_code >= 400:
                                raise httpx.StreamError(f"Request failed with status code {response.status_code}")
                            if downloaded_size > 0 and response.status_code == 200:
                                downloaded_size = 0
                                save_path.unlink(missing_ok=True)
                            if downloaded_size > 0 and response.status_code != 206:
                                raise httpx.StreamError("Server did not honor the byte-range resume request")
                            known_total_size = self._resolve_total_size(
                                response,
                                downloaded_size=downloaded_size,
                                known_total_size=known_total_size,
                            )
                            if active_progress is not None:
                                if task_id is None:
                                    task_id = active_progress.add_task(
                                        f"Downloading {save_path.name}",
                                        total=known_total_size,
                                        completed=downloaded_size,
                                    )
                                else:
                                    active_progress.update(
                                        task_id,
                                        total=known_total_size,
                                        completed=downloaded_size,
                                    )
                            open_mode = "ab" if downloaded_size > 0 else "wb"
                            with save_path.open(open_mode) as handle:
                                for chunk in response.iter_bytes(chunk_size):
                                    handle.write(chunk)
                                    if on_chunk_downloaded is not None:
                                        on_chunk_downloaded(len(chunk))
                                    downloaded_size += len(chunk)
                                    if active_progress is not None and task_id is not None:
                                        active_progress.update(
                                            task_id,
                                            total=known_total_size,
                                            completed=downloaded_size,
                                        )
                            return response
                    except httpx.RemoteProtocolError:
                        if not save_path.exists():
                            raise
                        downloaded_size = save_path.stat().st_size
                        if active_progress is not None and task_id is not None:
                            active_progress.update(
                                task_id,
                                total=known_total_size,
                                completed=downloaded_size,
                            )
                        if known_total_size is not None and downloaded_size >= known_total_size:
                            if last_response is None:
                                raise
                            return last_response
                        continue

        if last_response is not None:
            raise httpx.StreamError(f"Request failed with status code {last_response.status_code}")
        raise httpx.StreamError("Download interrupted before completion")

    def stream_download(
        self,
        *,
        path: str,
        save_path: Path,
        chunk_size: int = DEFAULT_TRANSFER_CHUNK_SIZE,
        show_progress: bool = False,
        on_chunk_downloaded: Callable[[int], None] | None = None,
    ) -> httpx.Response:
        try:
            request_func = cast(
                Callable[..., httpx.Response],
                self._get_retry()(self._stream_download),
            )
            result: httpx.Response = request_func(
                path=path,
                save_path=save_path,
                chunk_size=chunk_size,
                show_progress=show_progress,
                on_chunk_downloaded=on_chunk_downloaded,
            )
            if result.status_code >= 400:
                raise httpx.StreamError(f"Request failed with status code {result.status_code}")
            return result
        except RetryError as error:
            last_result = error.last_attempt.result()
            if isinstance(last_result, httpx.Response):
                if last_result.status_code >= 400:
                    raise httpx.StreamError(f"Request failed with status code {last_result.status_code}") from error
                return last_result
            raise error
