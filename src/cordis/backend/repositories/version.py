from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cordis.backend.models import Version
from cordis.backend.repositories.base import BaseRepository


class VersionRepository(BaseRepository[Version]):
    def __init__(self, session: AsyncSession):
        super().__init__(Version, session)

    async def get_by_repository_and_name(self, *, repository_id: int, name: str) -> Version | None:
        result = await self.session.execute(
            select(Version).where(Version.repository_id == repository_id, Version.name == name)
        )
        return result.scalar_one_or_none()

    async def list_for_repository(self, repository_id: int) -> list[Version]:
        result = await self.session.execute(select(Version).where(Version.repository_id == repository_id))
        return list(result.scalars().all())
