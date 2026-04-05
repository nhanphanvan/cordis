from typing import Annotated

from fastapi import APIRouter, Depends

from cordis.backend.api.dependencies import get_admin_user, get_current_user, get_uow
from cordis.backend.models import Role, User
from cordis.backend.repositories.unit_of_work import UnitOfWork
from cordis.backend.schemas.role import RoleCreateRequest, RoleListResponse, RoleResponse, RoleUpdateRequest
from cordis.backend.services.role import RoleService

router = APIRouter(prefix="/roles", tags=["roles"])
admin_router = APIRouter(prefix="/admin/roles", tags=["admin-roles"])


def _role_response(role: Role) -> RoleResponse:
    return RoleResponse(id=role.id, name=role.name, description=role.description)


@router.get("", response_model=RoleListResponse)
async def list_roles(
    _current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> RoleListResponse:
    roles = await RoleService(uow).list_roles()
    return RoleListResponse(items=[_role_response(role) for role in roles])


@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: int,
    _current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> RoleResponse:
    return _role_response(await RoleService(uow).get_role(role_id))


@admin_router.post("", response_model=RoleResponse, status_code=201)
async def create_role(
    request: RoleCreateRequest,
    _admin_user: Annotated[User, Depends(get_admin_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> RoleResponse:
    return _role_response(await RoleService(uow).create_role(name=request.name, description=request.description))


@admin_router.patch("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    request: RoleUpdateRequest,
    _admin_user: Annotated[User, Depends(get_admin_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> RoleResponse:
    role = await RoleService(uow).update_role(role_id, name=request.name, description=request.description)
    return _role_response(role)


@admin_router.delete("/{role_id}", response_model=RoleResponse)
async def delete_role(
    role_id: int,
    _admin_user: Annotated[User, Depends(get_admin_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> RoleResponse:
    return _role_response(await RoleService(uow).delete_role(role_id))
