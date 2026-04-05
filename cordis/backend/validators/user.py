from cordis.backend.exceptions import AppStatus, NotFoundError, NotUniqueError
from cordis.backend.models import User
from cordis.backend.repositories.unit_of_work import UnitOfWork
from cordis.backend.schemas.requests.user import UserCreateRequest, UserUpdateRequest

from .base import BaseValidator


class UserReadValidator(BaseValidator):
    @classmethod
    async def validate(cls, *, uow: UnitOfWork, user_id: int) -> User:
        user = await uow.users.get(user_id)
        if user is None:
            raise NotFoundError("User not found", app_status=AppStatus.ERROR_USER_NOT_FOUND)
        return user


class UserEmailReadValidator(BaseValidator):
    @classmethod
    async def validate(cls, *, uow: UnitOfWork, email: str) -> User:
        user = await uow.users.get_by_email(email)
        if user is None:
            raise NotFoundError("User not found", app_status=AppStatus.ERROR_USER_NOT_FOUND)
        return user


class UserCreateValidator(BaseValidator):
    @classmethod
    async def validate(cls, *, uow: UnitOfWork, request: UserCreateRequest) -> None:
        existing = await uow.users.get_by_email(request.email)
        if existing is not None:
            raise NotUniqueError("User email already exists", app_status=AppStatus.ERROR_USER_EMAIL_ALREADY_EXISTS)


class UserUpdateValidator(BaseValidator):
    @classmethod
    async def validate(cls, *, uow: UnitOfWork, user: User, request: UserUpdateRequest) -> User:
        if request.email is not None and request.email != user.email:
            existing = await uow.users.get_by_email(request.email)
            if existing is not None and existing.id != user.id:
                raise NotUniqueError("User email already exists", app_status=AppStatus.ERROR_USER_EMAIL_ALREADY_EXISTS)
        return user
