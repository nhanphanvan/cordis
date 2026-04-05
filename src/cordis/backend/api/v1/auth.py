from typing import Annotated

from fastapi import APIRouter, Depends

from cordis.backend.api.dependencies import get_admin_user, get_current_user, get_uow
from cordis.backend.models import User
from cordis.backend.repositories.unit_of_work import UnitOfWork
from cordis.backend.schemas.auth import CurrentUserResponse, LoginRequest, TokenResponse
from cordis.backend.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> TokenResponse:
    auth_service = AuthService(uow)
    return await auth_service.login(request)


@router.get("/me", response_model=CurrentUserResponse)
async def me(current_user: Annotated[User, Depends(get_current_user)]) -> CurrentUserResponse:
    return CurrentUserResponse(
        email=current_user.email,
        is_active=current_user.is_active,
        is_admin=current_user.is_admin,
    )


@router.get("/admin-check", response_model=CurrentUserResponse)
async def admin_check(current_user: Annotated[User, Depends(get_admin_user)]) -> CurrentUserResponse:
    return CurrentUserResponse(
        email=current_user.email,
        is_active=current_user.is_active,
        is_admin=current_user.is_admin,
    )
