from typing import Annotated

from fastapi import Depends, Request

from cordis.backend.api.dependencies.database import get_uow
from cordis.backend.models import User
from cordis.backend.repositories.unit_of_work import UnitOfWork
from cordis.backend.security import BearerTokenAuthenticationBackend
from cordis.backend.validators.auth import CurrentUserValidator


async def get_optional_current_user(
    request: Request,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> User | None:
    userinfo = await BearerTokenAuthenticationBackend().authenticate(request, uow)
    if userinfo is None:
        return None
    return await CurrentUserValidator.validate(uow=uow, userinfo=userinfo)
