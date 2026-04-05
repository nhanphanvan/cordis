from typing import Annotated

from fastapi import Depends, Path
from fastapi.security import HTTPAuthorizationCredentials

from cordis.backend.api.dependencies.auth import bearer_scheme
from cordis.backend.api.dependencies.database import get_uow
from cordis.backend.models import User
from cordis.backend.repositories.unit_of_work import UnitOfWork
from cordis.backend.services.auth import AuthService
from cordis.backend.services.authorization import AuthorizationService, RepositoryAccessContext
from cordis.shared.errors import AuthenticationError


async def get_optional_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> User | None:
    if credentials is None or not credentials.credentials:
        return None
    auth_service = AuthService(uow)
    return await auth_service.get_current_user(credentials.credentials)


async def require_repository_viewer(
    repository_id: Annotated[int, Path()],
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> RepositoryAccessContext:
    return await AuthorizationService(uow).require_repository_access(
        repository_id=repository_id,
        required_role="viewer",
        current_user=current_user,
    )


async def require_repository_developer(
    repository_id: Annotated[int, Path()],
    current_user: Annotated[User, Depends(get_optional_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> RepositoryAccessContext:
    if current_user is None:
        raise AuthenticationError("Missing bearer token")
    return await AuthorizationService(uow).require_repository_access(
        repository_id=repository_id,
        required_role="developer",
        current_user=current_user,
    )


async def require_repository_owner_or_admin(
    repository_id: Annotated[int, Path()],
    current_user: Annotated[User, Depends(get_optional_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> RepositoryAccessContext:
    if current_user is None:
        raise AuthenticationError("Missing bearer token")
    return await AuthorizationService(uow).require_repository_access(
        repository_id=repository_id,
        required_role="owner",
        current_user=current_user,
    )
