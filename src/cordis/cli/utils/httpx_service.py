from typing import Any

import httpx
from tenacity import RetryError, retry, retry_if_exception_type, retry_if_result, stop_after_attempt, wait_exponential


# Define the conditions for retrying based on HTTP status codes
def is_retryable_status_code(response: httpx.Response) -> bool:
    return response.status_code in [429, 502, 503, 504]


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
        """Async HTTP transport with retries and sane client defaults."""
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
            response = await client.request(method=method, url=path, **kwargs)
            return response

    async def _request_with_retry(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        try:
            retry_decorator = self._get_retry()
            request_func = retry_decorator(self._request)
            result: httpx.Response = await request_func(method, path, **kwargs)
            return result
        except RetryError as error:
            last_result = error.last_attempt.result()
            if isinstance(last_result, httpx.Response):
                return last_result
            raise error

    async def request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        return await self._request_with_retry(method, path, **kwargs)

    async def get(self, path: str, **kwargs: Any) -> httpx.Response:
        return await self._request_with_retry("GET", path, **kwargs)

    async def post(self, path: str, **kwargs: Any) -> httpx.Response:
        return await self._request_with_retry("POST", path, **kwargs)

    async def put(self, path: str, **kwargs: Any) -> httpx.Response:
        return await self._request_with_retry("PUT", path, **kwargs)

    async def delete(self, path: str, **kwargs: Any) -> httpx.Response:
        return await self._request_with_retry("DELETE", path, **kwargs)

    async def head(self, path: str, **kwargs: Any) -> httpx.Response:
        return await self._request_with_retry("HEAD", path, **kwargs)

    async def patch(self, path: str, **kwargs: Any) -> httpx.Response:
        return await self._request_with_retry("PATCH", path, **kwargs)
