from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cordis.backend.models import Role
from cordis.backend.repositories.base import BaseRepository


class RoleRepository(BaseRepository[Role]):
    def __init__(self, session: AsyncSession):
        super().__init__(Role, session)

    async def get_by_name(self, name: str) -> Role | None:
        result = await self.session.execute(select(Role).where(Role.name == name))
        return result.scalar_one_or_none()
