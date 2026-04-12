from typing import Any

from cordis.sdk.apis.base import BaseAPI


class UsersAPI(BaseAPI):
    async def get_me(self) -> dict[str, Any]:
        return await self._request(method="GET", path="/api/v1/users/me")

    async def list_users(self) -> list[dict[str, Any]]:
        response = await self._request(method="GET", path="/api/v1/admin/users")
        return list(response.get("items", []))

    async def get_user(self, *, user_id: int) -> dict[str, Any]:
        return await self._request(method="GET", path=f"/api/v1/users/{user_id}")

    async def get_user_by_email(self, *, email: str) -> dict[str, Any]:
        return await self._request(method="GET", path=f"/api/v1/users/emails/{email}")

    async def list_my_repositories(self) -> list[dict[str, Any]]:
        response = await self._request(method="GET", path="/api/v1/users/me/repositories")
        return list(response.get("items", []))
