from typing import Any

from cordis.cli.sdk.apis.base import BaseAPI


class RepositoriesAPI(BaseAPI):
    async def create_repository(
        self,
        *,
        name: str,
        visibility: str,
        allow_public_object_urls: bool,
    ) -> dict[str, Any]:
        return await self._request(
            method="POST",
            path="/api/v1/repositories",
            payload={
                "name": name,
                "description": name,
                "visibility": visibility,
                "allow_public_object_urls": allow_public_object_urls,
            },
        )

    async def update_repository(
        self,
        *,
        repository_id: int,
        visibility: str,
        allow_public_object_urls: bool,
    ) -> dict[str, Any]:
        return await self._request(
            method="PATCH",
            path=f"/api/v1/repositories/{repository_id}",
            payload={
                "visibility": visibility,
                "allow_public_object_urls": allow_public_object_urls,
            },
        )

    async def delete_repository(self, *, repository_id: int) -> dict[str, Any]:
        return await self._request(method="DELETE", path=f"/api/v1/repositories/{repository_id}")

    async def list_repository_versions(self, *, repository_id: int) -> list[dict[str, Any]]:
        response = await self._request(method="GET", path=f"/api/v1/repositories/{repository_id}/versions")
        return list(response.get("items", []))

    async def list_repository_members(self, *, repository_id: int) -> list[dict[str, Any]]:
        response = await self._request(method="GET", path=f"/api/v1/repositories/{repository_id}/members")
        return list(response.get("items", []))

    async def add_repository_member(self, *, repository_id: int, email: str, role: str) -> dict[str, Any]:
        user = await self.client.users.get_user_by_email(email=email)
        return await self._request(
            method="POST",
            path=f"/api/v1/repositories/{repository_id}/members",
            payload={"user_id": user["id"], "role": role},
        )

    async def update_repository_member(self, *, repository_id: int, email: str, role: str) -> dict[str, Any]:
        user = await self.client.users.get_user_by_email(email=email)
        return await self._request(
            method="PATCH",
            path=f"/api/v1/repositories/{repository_id}/members/{user['id']}",
            payload={"role": role},
        )

    async def delete_repository_member(self, *, repository_id: int, email: str) -> dict[str, Any]:
        user = await self.client.users.get_user_by_email(email=email)
        return await self._request(
            method="DELETE",
            path=f"/api/v1/repositories/{repository_id}/members/{user['id']}",
        )
