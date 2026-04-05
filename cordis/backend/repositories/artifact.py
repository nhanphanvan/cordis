from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cordis.backend.models import Artifact
from cordis.backend.repositories.base import BaseRepository


class ArtifactRepository(BaseRepository[Artifact]):
    def __init__(self, session: AsyncSession):
        super().__init__(Artifact, session)

    async def get_by_repository_and_path(self, *, repository_id: int, path: str) -> Artifact | None:
        result = await self.session.execute(
            select(Artifact).where(Artifact.repository_id == repository_id, Artifact.path == path)
        )
        return result.scalar_one_or_none()
