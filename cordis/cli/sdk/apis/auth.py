from cordis.cli.sdk.apis.base import BaseAPI


class AuthAPI(BaseAPI):
    async def login(self, *, email: str, password: str) -> str:
        response = await self._request(
            method="POST",
            path="/api/v1/auth/login",
            payload={"email": email, "password": password},
        )
        return str(response["access_token"])
