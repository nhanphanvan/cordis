from fastapi import Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from cordis.backend.repositories.unit_of_work import UnitOfWork
from cordis.backend.security.core import verify_access_token
from cordis.backend.security.userinfo import UserInfo

from .base import BaseAuthenticationBackend


class BearerTokenAuthenticationBackend(BaseAuthenticationBackend):
    scheme = HTTPBearer(auto_error=False)

    async def authenticate(self, request: Request, uow: UnitOfWork) -> UserInfo | None:
        credentials: HTTPAuthorizationCredentials | None = await self.scheme(request)
        if credentials is None or not credentials.credentials:
            return None

        payload = verify_access_token(credentials.credentials)
        identity = str(payload["sub"])
        user = await uow.users.get(int(identity))
        if user is None:
            return None
        return UserInfo(email=user.email, identity=identity, is_admin=user.is_admin)
