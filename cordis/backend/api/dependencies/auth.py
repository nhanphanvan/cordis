from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from cordis.backend.api.dependencies.database import get_uow
from cordis.backend.exceptions import AppStatus, UnauthorizedError
from cordis.backend.models import User
from cordis.backend.repositories.unit_of_work import UnitOfWork
from cordis.backend.validators.auth import CurrentUserValidator

bearer_scheme = HTTPBearer(auto_error=False)


async def get_bearer_credentials(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> str:
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError("Missing bearer token", app_status=AppStatus.ERROR_MISSING_BEARER_TOKEN)
    return credentials.credentials


async def get_current_user(
    token: Annotated[str, Depends(get_bearer_credentials)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> User:
    return await CurrentUserValidator.validate(uow=uow, token=token)


async def get_admin_user(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user
