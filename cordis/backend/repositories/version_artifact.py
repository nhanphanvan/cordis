from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cordis.backend.models import VersionArtifact
from cordis.backend.repositories.base import BaseRepository


class VersionArtifactRepository(BaseRepository[VersionArtifact]):
    def __init__(self, session: AsyncSession):
        super().__init__(VersionArtifact, session)

    async def get_for_version_and_artifact(self, *, version_id: str, artifact_id: str) -> VersionArtifact | None:
        result = await self.session.execute(
            select(VersionArtifact)
            .where(VersionArtifact.version_id == version_id, VersionArtifact.artifact_id == artifact_id)
            .options(selectinload(VersionArtifact.artifact))
        )
        return result.scalar_one_or_none()

    async def get_for_version_and_path(self, *, version_id: str, path: str) -> VersionArtifact | None:
        result = await self.session.execute(
            select(VersionArtifact)
            .join(VersionArtifact.artifact)
            .where(VersionArtifact.version_id == version_id, VersionArtifact.artifact.has(path=path))
            .options(selectinload(VersionArtifact.artifact))
        )
        return result.scalar_one_or_none()

    async def list_for_version(self, version_id: str) -> list[VersionArtifact]:
        result = await self.session.execute(
            select(VersionArtifact)
            .where(VersionArtifact.version_id == version_id)
            .options(selectinload(VersionArtifact.artifact))
        )
        return list(result.scalars().all())
