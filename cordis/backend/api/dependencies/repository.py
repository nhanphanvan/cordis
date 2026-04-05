from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials

from cordis.backend.api.dependencies.auth import bearer_scheme
from cordis.backend.api.dependencies.database import get_uow
from cordis.backend.models import User
from cordis.backend.repositories.unit_of_work import UnitOfWork
from cordis.backend.validators.auth import CurrentUserValidator


async def get_optional_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> User | None:
    if credentials is None or not credentials.credentials:
        return None
    return await CurrentUserValidator.validate(uow=uow, token=credentials.credentials)
