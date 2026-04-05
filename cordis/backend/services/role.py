from cordis.backend.errors import ConflictError, NotFoundError
from cordis.backend.models import Role
from cordis.backend.repositories.unit_of_work import UnitOfWork


class RoleService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def get_role(self, role_id: int) -> Role:
        role = await self.uow.roles.get(role_id)
        if role is None:
            raise NotFoundError("Role not found")
        return role

    async def list_roles(self) -> list[Role]:
        roles, _ = await self.uow.roles.list()
        return list(roles)

    async def create_role(self, *, name: str, description: str | None) -> Role:
        existing = await self.uow.roles.get_by_name(name)
        if existing is not None:
            raise ConflictError("Role name already exists")
        role = await self.uow.roles.create(name=name, description=description)
        await self.uow.commit()
        return role

    async def update_role(self, role_id: int, *, name: str | None = None, description: str | None = None) -> Role:
        role = await self.get_role(role_id)
        if name is not None and name != role.name:
            existing = await self.uow.roles.get_by_name(name)
            if existing is not None and existing.id != role.id:
                raise ConflictError("Role name already exists")
            role.name = name
        if description is not None:
            role.description = description
        await self.uow.commit()
        return role

    async def delete_role(self, role_id: int) -> Role:
        role = await self.get_role(role_id)
        await self.uow.roles.delete(role)
        await self.uow.commit()
        return role
