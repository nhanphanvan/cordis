from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cordis.backend.models import VersionTag
from cordis.backend.repositories.base import BaseRepository


class VersionTagRepository(BaseRepository[VersionTag]):
    def __init__(self, session: AsyncSession):
        super().__init__(VersionTag, session)

    async def get_with_version(self, tag_id: UUID) -> VersionTag | None:
        result = await self.session.execute(
            select(VersionTag).where(VersionTag.id == tag_id).options(selectinload(VersionTag.version))
        )
        return result.scalar_one_or_none()

    async def get_by_repository_and_name(self, *, repository_id: int, name: str) -> VersionTag | None:
        result = await self.session.execute(
            select(VersionTag)
            .where(VersionTag.repository_id == repository_id, VersionTag.name == name)
            .options(selectinload(VersionTag.version))
        )
        return result.scalar_one_or_none()

    async def list_for_repository(self, repository_id: int) -> list[VersionTag]:
        result = await self.session.execute(
            select(VersionTag)
            .where(VersionTag.repository_id == repository_id)
            .options(selectinload(VersionTag.version))
        )
        return list(result.scalars().all())
