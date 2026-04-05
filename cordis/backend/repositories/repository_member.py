from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cordis.backend.models import RepositoryMember
from cordis.backend.repositories.base import BaseRepository


class RepositoryMemberRepository(BaseRepository[RepositoryMember]):
    def __init__(self, session: AsyncSession):
        super().__init__(RepositoryMember, session)

    async def get_for_user_and_repository(self, *, user_id: int, repository_id: int) -> RepositoryMember | None:
        result = await self.session.execute(
            select(RepositoryMember)
            .where(RepositoryMember.user_id == user_id, RepositoryMember.repository_id == repository_id)
            .options(selectinload(RepositoryMember.role), selectinload(RepositoryMember.user))
        )
        return result.scalar_one_or_none()

    async def list_for_repository(self, repository_id: int) -> list[RepositoryMember]:
        result = await self.session.execute(
            select(RepositoryMember)
            .where(RepositoryMember.repository_id == repository_id)
            .options(selectinload(RepositoryMember.role), selectinload(RepositoryMember.user))
        )
        return list(result.scalars().all())

    async def list_for_user(self, user_id: int) -> list[RepositoryMember]:
        result = await self.session.execute(
            select(RepositoryMember)
            .where(RepositoryMember.user_id == user_id)
            .options(selectinload(RepositoryMember.role), selectinload(RepositoryMember.repository))
        )
        return list(result.scalars().all())

    async def delete_for_user_and_repository(self, *, user_id: int, repository_id: int) -> RepositoryMember | None:
        membership = await self.get_for_user_and_repository(user_id=user_id, repository_id=repository_id)
        if membership is None:
            return None
        await self.delete(membership)
        return membership
