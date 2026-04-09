from typing import Any

from cordis.cli.sdk.apis.base import BaseAPI


class VersionsAPI(BaseAPI):
    async def get_version(self, *, repository_id: int, name: str) -> dict[str, Any]:
        return await self._request(
            method="GET",
            path=f"/api/v1/versions?repository_id={repository_id}&name={name}",
        )

    async def create_version(self, *, repository_id: int, name: str) -> dict[str, Any]:
        return await self._request(
            method="POST",
            path="/api/v1/versions",
            payload={"repository_id": repository_id, "name": name},
        )

    async def delete_version(self, *, repository_id: int, name: str) -> None:
        version = await self.get_version(repository_id=repository_id, name=name)
        await self._request(method="DELETE", path=f"/api/v1/versions/{version['id']}")

    async def download_item(
        self,
        *,
        repository_id: int,
        version_name: str,
        path: str,
        save_path: str,
    ) -> dict[str, Any]:
        version = await self.get_version(repository_id=repository_id, name=version_name)
        artifact = await self._request(
            method="GET",
            path=f"/api/v1/versions/{version['id']}/artifacts/by-path?path={path}",
        )
        download = await self._request(
            method="POST",
            path=f"/api/v1/versions/{version['id']}/artifacts/{artifact['id']}/download",
        )
        download["save_path"] = save_path
        return download

    async def list_version_artifacts(self, *, repository_id: int, version_name: str) -> list[dict[str, Any]]:
        version = await self.get_version(repository_id=repository_id, name=version_name)
        response = await self._request(method="GET", path=f"/api/v1/versions/{version['id']}/artifacts")
        return list(response.get("items", []))
