from fastapi import Request

from cordis.backend.repositories.unit_of_work import UnitOfWork
from cordis.backend.security.userinfo import UserInfo


class BaseAuthenticationBackend:
    async def authenticate(self, request: Request, uow: UnitOfWork) -> UserInfo | None:
        raise NotImplementedError
