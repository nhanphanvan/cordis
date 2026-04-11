from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cordis.backend.constants import UPLOAD_RESUMABLE_STATUSES
from cordis.backend.models import UploadSession
from cordis.backend.repositories.base import BaseRepository


class UploadSessionRepository(BaseRepository[UploadSession]):
    def __init__(self, session: AsyncSession):
        super().__init__(UploadSession, session)

    async def get_resumable(
        self,
        *,
        version_id: UUID,
        path: str,
        checksum: str,
        size: int,
    ) -> UploadSession | None:
        result = await self.session.execute(
            select(UploadSession).where(
                UploadSession.version_id == version_id,
                UploadSession.path == path,
                UploadSession.checksum == checksum,
                UploadSession.size == size,
                UploadSession.status.in_(UPLOAD_RESUMABLE_STATUSES),
            )
        )
        return result.scalar_one_or_none()
