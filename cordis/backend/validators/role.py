from cordis.backend.exceptions import AppStatus, NotFoundError, NotUniqueError
from cordis.backend.models import Role
from cordis.backend.repositories.unit_of_work import UnitOfWork
from cordis.backend.schemas.requests.role import RoleCreateRequest, RoleUpdateRequest

from .base import BaseValidator


class RoleReadValidator(BaseValidator):
    @classmethod
    async def validate(cls, *, uow: UnitOfWork, role_id: int) -> Role:
        role = await uow.roles.get(role_id)
        if role is None:
            raise NotFoundError("Role not found", app_status=AppStatus.ERROR_ROLE_NOT_FOUND)
        return role


class RoleCreateValidator(BaseValidator):
    @classmethod
    async def validate(cls, *, uow: UnitOfWork, request: RoleCreateRequest) -> None:
        existing = await uow.roles.get_by_name(request.name)
        if existing is not None:
            raise NotUniqueError("Role name already exists", app_status=AppStatus.ERROR_ROLE_NAME_ALREADY_EXISTS)


class RoleUpdateValidator(BaseValidator):
    @classmethod
    async def validate(cls, *, uow: UnitOfWork, role: Role, request: RoleUpdateRequest) -> Role:
        if request.name is not None and request.name != role.name:
            existing = await uow.roles.get_by_name(request.name)
            if existing is not None and existing.id != role.id:
                raise NotUniqueError("Role name already exists", app_status=AppStatus.ERROR_ROLE_NAME_ALREADY_EXISTS)
        return role
