from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cordis.backend.models import UploadSessionPart
from cordis.backend.repositories.base import BaseRepository


class UploadSessionPartRepository(BaseRepository[UploadSessionPart]):
    def __init__(self, session: AsyncSession):
        super().__init__(UploadSessionPart, session)

    async def get_for_session_and_part_number(
        self,
        *,
        session_id: UUID,
        part_number: int,
    ) -> UploadSessionPart | None:
        result = await self.session.execute(
            select(UploadSessionPart).where(
                UploadSessionPart.session_id == session_id,
                UploadSessionPart.part_number == part_number,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_session(self, session_id: UUID) -> list[UploadSessionPart]:
        result = await self.session.execute(
            select(UploadSessionPart)
            .where(UploadSessionPart.session_id == session_id)
            .order_by(UploadSessionPart.part_number.asc())
        )
        return list(result.scalars().all())
