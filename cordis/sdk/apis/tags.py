from typing import Any

from cordis.sdk.apis.base import BaseAPI


class TagsAPI(BaseAPI):
    async def list_tags(self, *, repository_id: int) -> list[dict[str, Any]]:
        response = await self._request(method="GET", path=f"/api/v1/repositories/{repository_id}/tags")
        return list(response.get("items", []))

    async def get_tag(self, *, repository_id: int, name: str) -> dict[str, Any]:
        return await self._request(method="GET", path=f"/api/v1/tags?repository_id={repository_id}&name={name}")

    async def create_tag(self, *, repository_id: int, version_name: str, name: str) -> dict[str, Any]:
        version = await self.client.versions.get_version(repository_id=repository_id, name=version_name)
        return await self._request(
            method="POST",
            path="/api/v1/tags",
            payload={"repository_id": repository_id, "version_id": version["id"], "name": name},
        )

    async def delete_tag(self, *, repository_id: int, name: str) -> None:
        tag = await self.get_tag(repository_id=repository_id, name=name)
        await self._request(method="DELETE", path=f"/api/v1/tags/{tag['id']}")
