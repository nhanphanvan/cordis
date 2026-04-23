from typing import Annotated

from fastapi import APIRouter, Depends

from cordis.backend.api.dependencies import get_current_user, get_uow
from cordis.backend.exceptions import AppStatus
from cordis.backend.models import User
from cordis.backend.policies import UserPolicy, authorize
from cordis.backend.repositories.unit_of_work import UnitOfWork
from cordis.backend.schemas.requests.user import UserCreateRequest, UserUpdateRequest
from cordis.backend.schemas.responses.user import (
    UserListResponse,
    UserRepositoryItem,
    UserRepositoryListResponse,
    UserResponse,
)
from cordis.backend.services.user import UserService
from cordis.backend.validators.user import (
    UserCreateValidator,
    UserEmailReadValidator,
    UserReadValidator,
    UserUpdateValidator,
)

router = APIRouter(prefix="/users", tags=["users"])


def _user_response(user: User) -> UserResponse:
    return UserResponse(id=user.id, email=user.email, name=user.name, is_active=user.is_active, is_admin=user.is_admin)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: Annotated[User, Depends(get_current_user)]) -> UserResponse:
    return _user_response(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_me(
    request: UserUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> UserResponse:
    user = await UserUpdateValidator.validate(uow=uow, user=current_user, request=request)
    updated = await UserService(uow).update_user(user, email=request.email, name=request.name)
    return _user_response(updated)


@router.get("/me/repositories", response_model=UserRepositoryListResponse)
async def get_my_repositories(
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> UserRepositoryListResponse:
    memberships = await uow.repository_members.list_for_user(current_user.id)
    return UserRepositoryListResponse(
        items=[
            UserRepositoryItem(
                repository_id=membership.repository_id,
                repository_name=membership.repository.name,
                role_name=membership.role.name,
            )
            for membership in memberships
        ]
    )


@router.get("/emails/{email}", response_model=UserResponse)
async def get_user_by_email(
    email: str,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> UserResponse:
    await authorize(current_user, UserPolicy.authenticated)
    return _user_response(await UserEmailReadValidator.validate(uow=uow, email=email))


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> UserResponse:
    await authorize(current_user, UserPolicy.authenticated)
    return _user_response(await UserReadValidator.validate(uow=uow, user_id=user_id))


@router.get("", response_model=UserListResponse)
async def list_users(
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> UserListResponse:
    await authorize(
        current_user,
        UserPolicy.admin,
        message="Admin privileges required",
        app_status=AppStatus.ERROR_ADMIN_PRIVILEGES_REQUIRED,
    )
    users = await UserService(uow).list_users()
    return UserListResponse(items=[_user_response(user) for user in users])


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    request: UserCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> UserResponse:
    await authorize(
        current_user,
        UserPolicy.admin,
        message="Admin privileges required",
        app_status=AppStatus.ERROR_ADMIN_PRIVILEGES_REQUIRED,
    )
    await UserCreateValidator.validate(uow=uow, request=request)
    user = await UserService(uow).create_user(
        email=request.email,
        name=request.name,
        password=request.password,
        is_active=request.is_active,
        is_admin=request.is_admin,
    )
    return _user_response(user)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    request: UserUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> UserResponse:
    await authorize(
        current_user,
        UserPolicy.admin,
        message="Admin privileges required",
        app_status=AppStatus.ERROR_ADMIN_PRIVILEGES_REQUIRED,
    )
    user = await UserReadValidator.validate(uow=uow, user_id=user_id)
    user = await UserUpdateValidator.validate(uow=uow, user=user, request=request)
    user = await UserService(uow).update_user(
        user,
        email=request.email,
        name=request.name,
        is_active=request.is_active,
        is_admin=request.is_admin,
    )
    return _user_response(user)


@router.delete("/{user_id}", response_model=UserResponse)
async def delete_user(
    user_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> UserResponse:
    await authorize(
        current_user,
        UserPolicy.admin,
        message="Admin privileges required",
        app_status=AppStatus.ERROR_ADMIN_PRIVILEGES_REQUIRED,
    )
    user = await UserReadValidator.validate(uow=uow, user_id=user_id)
    return _user_response(await UserService(uow).delete_user(user))
