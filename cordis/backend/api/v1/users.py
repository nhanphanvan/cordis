from typing import Annotated

from fastapi import APIRouter, Depends

from cordis.backend.api.dependencies import get_admin_user, get_current_user, get_uow
from cordis.backend.models import User
from cordis.backend.repositories.unit_of_work import UnitOfWork
from cordis.backend.schemas.requests.user import UserCreateRequest, UserUpdateRequest
from cordis.backend.schemas.responses.user import (
    UserListResponse,
    UserRepositoryItem,
    UserRepositoryListResponse,
    UserResponse,
)
from cordis.backend.services.user import UserService

router = APIRouter(prefix="/users", tags=["users"])
admin_router = APIRouter(prefix="/admin/users", tags=["admin-users"])


def _user_response(user: User) -> UserResponse:
    return UserResponse(id=user.id, email=user.email, is_active=user.is_active, is_admin=user.is_admin)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: Annotated[User, Depends(get_current_user)]) -> UserResponse:
    return _user_response(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_me(
    request: UserUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> UserResponse:
    updated = await UserService(uow).update_user(current_user.id, email=request.email)
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
    _current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> UserResponse:
    return _user_response(await UserService(uow).get_user_by_email(email))


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    _current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> UserResponse:
    return _user_response(await UserService(uow).get_user(user_id))


@admin_router.get("", response_model=UserListResponse)
async def list_users(
    _admin_user: Annotated[User, Depends(get_admin_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> UserListResponse:
    users = await UserService(uow).list_users()
    return UserListResponse(items=[_user_response(user) for user in users])


@admin_router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    request: UserCreateRequest,
    _admin_user: Annotated[User, Depends(get_admin_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> UserResponse:
    user = await UserService(uow).create_user(
        email=request.email,
        password=request.password,
        is_active=request.is_active,
        is_admin=request.is_admin,
    )
    return _user_response(user)


@admin_router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    request: UserUpdateRequest,
    _admin_user: Annotated[User, Depends(get_admin_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> UserResponse:
    user = await UserService(uow).update_user(
        user_id,
        email=request.email,
        is_active=request.is_active,
        is_admin=request.is_admin,
    )
    return _user_response(user)


@admin_router.delete("/{user_id}", response_model=UserResponse)
async def delete_user(
    user_id: int,
    _admin_user: Annotated[User, Depends(get_admin_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> UserResponse:
    return _user_response(await UserService(uow).delete_user(user_id))
