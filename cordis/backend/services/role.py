from cordis.backend.models import Role
from cordis.backend.repositories.unit_of_work import UnitOfWork


class RoleService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def get_role(self, role_id: int) -> Role | None:
        return await self.uow.roles.get(role_id)

    async def list_roles(self) -> list[Role]:
        roles, _ = await self.uow.roles.list()
        return list(roles)

    async def create_role(self, *, name: str, description: str | None) -> Role:
        role = await self.uow.roles.create(name=name, description=description)
        await self.uow.commit()
        return role

    async def update_role(self, role: Role, *, name: str | None = None, description: str | None = None) -> Role:
        if name is not None and name != role.name:
            role.name = name
        if description is not None:
            role.description = description
        await self.uow.commit()
        return role

    async def delete_role(self, role: Role) -> Role:
        await self.uow.roles.delete(role)
        await self.uow.commit()
        return role
