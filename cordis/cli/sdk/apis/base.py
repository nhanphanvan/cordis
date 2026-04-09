from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cordis.cli.sdk.client import CordisClient


@dataclass(slots=True)
class BaseAPI:
    client: CordisClient

    async def _request(
        self,
        *,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await self.client.request(method=method, path=path, payload=payload)
