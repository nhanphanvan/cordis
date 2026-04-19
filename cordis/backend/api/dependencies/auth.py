from typing import Annotated

from fastapi import Depends, Request

from cordis.backend.api.dependencies.database import get_uow
from cordis.backend.exceptions import AppStatus, NotFoundError, UnauthorizedError
from cordis.backend.models import User
from cordis.backend.repositories.unit_of_work import UnitOfWork
from cordis.backend.security import BearerTokenAuthenticationBackend


async def _resolve_current_user(request: Request, uow: UnitOfWork, *, required: bool) -> User | None:
    userinfo = await BearerTokenAuthenticationBackend().authenticate(request, uow)
    if userinfo is None:
        if required:
            raise UnauthorizedError("Missing bearer token", app_status=AppStatus.ERROR_MISSING_BEARER_TOKEN)
        return None

    user = await uow.users.get(int(userinfo.identity))
    if user is None:
        raise NotFoundError("User not found", app_status=AppStatus.ERROR_USER_NOT_FOUND)
    if not user.is_active:
        raise UnauthorizedError("Invalid bearer token", app_status=AppStatus.ERROR_INVALID_BEARER_TOKEN)
    return user


async def get_current_user(
    request: Request,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    _bearer: Annotated[str | None, Depends(BearerTokenAuthenticationBackend.scheme)],
) -> User:
    user = await _resolve_current_user(request, uow, required=True)
    assert user is not None
    return user


async def get_optional_current_user(
    request: Request,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    _bearer: Annotated[str | None, Depends(BearerTokenAuthenticationBackend.scheme)],
) -> User | None:
    return await _resolve_current_user(request, uow, required=False)
