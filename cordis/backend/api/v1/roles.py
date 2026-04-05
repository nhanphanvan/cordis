from typing import Annotated

from fastapi import APIRouter, Depends

from cordis.backend.api.dependencies import get_current_user, get_uow
from cordis.backend.exceptions import AppStatus
from cordis.backend.models import Role, User
from cordis.backend.policies import RolePolicy, authorize
from cordis.backend.repositories.unit_of_work import UnitOfWork
from cordis.backend.schemas.requests.role import RoleCreateRequest, RoleUpdateRequest
from cordis.backend.schemas.responses.role import RoleListResponse, RoleResponse
from cordis.backend.services.role import RoleService
from cordis.backend.validators.role import RoleCreateValidator, RoleReadValidator, RoleUpdateValidator

router = APIRouter(prefix="/roles", tags=["roles"])
admin_router = APIRouter(prefix="/admin/roles", tags=["admin-roles"])


def _role_response(role: Role) -> RoleResponse:
    return RoleResponse(id=role.id, name=role.name, description=role.description)


@router.get("", response_model=RoleListResponse)
async def list_roles(
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> RoleListResponse:
    await authorize(current_user, RolePolicy.read)
    roles = await RoleService(uow).list_roles()
    return RoleListResponse(items=[_role_response(role) for role in roles])


@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> RoleResponse:
    await authorize(current_user, RolePolicy.read)
    return _role_response(await RoleReadValidator.validate(uow=uow, role_id=role_id))


@admin_router.post("", response_model=RoleResponse, status_code=201)
async def create_role(
    request: RoleCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> RoleResponse:
    await authorize(
        current_user,
        RolePolicy.admin,
        message="Admin privileges required",
        app_status=AppStatus.ERROR_ADMIN_PRIVILEGES_REQUIRED,
    )
    await RoleCreateValidator.validate(uow=uow, request=request)
    return _role_response(await RoleService(uow).create_role(name=request.name, description=request.description))


@admin_router.patch("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    request: RoleUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> RoleResponse:
    await authorize(
        current_user,
        RolePolicy.admin,
        message="Admin privileges required",
        app_status=AppStatus.ERROR_ADMIN_PRIVILEGES_REQUIRED,
    )
    role = await RoleReadValidator.validate(uow=uow, role_id=role_id)
    role = await RoleUpdateValidator.validate(uow=uow, role=role, request=request)
    role = await RoleService(uow).update_role(role, name=request.name, description=request.description)
    return _role_response(role)


@admin_router.delete("/{role_id}", response_model=RoleResponse)
async def delete_role(
    role_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> RoleResponse:
    await authorize(
        current_user,
        RolePolicy.admin,
        message="Admin privileges required",
        app_status=AppStatus.ERROR_ADMIN_PRIVILEGES_REQUIRED,
    )
    role = await RoleReadValidator.validate(uow=uow, role_id=role_id)
    return _role_response(await RoleService(uow).delete_role(role))
