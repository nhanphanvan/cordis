from typing import Annotated

from fastapi import APIRouter, Depends

from cordis.backend.api.dependencies import get_current_user, get_uow
from cordis.backend.exceptions import AppStatus
from cordis.backend.models import User
from cordis.backend.policies import AuthPolicy, authorize
from cordis.backend.repositories.unit_of_work import UnitOfWork
from cordis.backend.schemas.requests.auth import LoginRequest
from cordis.backend.schemas.responses.auth import CurrentUserResponse, TokenResponse
from cordis.backend.services.auth import AuthService
from cordis.backend.validators.auth import LoginValidator

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> TokenResponse:
    user = await LoginValidator.validate(uow=uow, request=request)
    return await AuthService(uow).login(user)


@router.get("/me", response_model=CurrentUserResponse)
async def me(current_user: Annotated[User, Depends(get_current_user)]) -> CurrentUserResponse:
    return CurrentUserResponse(
        email=current_user.email,
        name=current_user.name,
        is_active=current_user.is_active,
        is_admin=current_user.is_admin,
    )


@router.get("/admin-check", response_model=CurrentUserResponse)
async def admin_check(current_user: Annotated[User, Depends(get_current_user)]) -> CurrentUserResponse:
    await authorize(
        current_user,
        AuthPolicy.admin,
        message="Admin privileges required",
        app_status=AppStatus.ERROR_ADMIN_PRIVILEGES_REQUIRED,
    )
    return CurrentUserResponse(
        email=current_user.email,
        name=current_user.name,
        is_active=current_user.is_active,
        is_admin=current_user.is_admin,
    )
