from cordis.backend.exceptions import AppStatus, NotFoundError, UnauthorizedError
from cordis.backend.models import User
from cordis.backend.repositories.unit_of_work import UnitOfWork
from cordis.backend.schemas.requests.auth import LoginRequest
from cordis.backend.security import UserInfo, verify_password

from .base import BaseValidator


class LoginValidator(BaseValidator):
    @classmethod
    async def validate(cls, *, uow: UnitOfWork, request: LoginRequest) -> User:
        user = await uow.users.get_by_email(request.email)
        if user is None or not user.is_active:
            raise UnauthorizedError("Invalid credentials", app_status=AppStatus.ERROR_INVALID_CREDENTIALS)
        if not verify_password(request.password, user.password_hash):
            raise UnauthorizedError("Invalid credentials", app_status=AppStatus.ERROR_INVALID_CREDENTIALS)
        return user


class CurrentUserValidator(BaseValidator):
    @classmethod
    async def validate(cls, *, uow: UnitOfWork, userinfo: UserInfo) -> User:
        user = await uow.users.get(int(userinfo.identity))
        if user is None:
            raise NotFoundError("User not found", app_status=AppStatus.ERROR_USER_NOT_FOUND)
        if not user.is_active:
            raise UnauthorizedError("Invalid bearer token", app_status=AppStatus.ERROR_INVALID_BEARER_TOKEN)
        return user
