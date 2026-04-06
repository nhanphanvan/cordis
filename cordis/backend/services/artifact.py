from uuid import UUID

from cordis.backend.models import Artifact, Repository
from cordis.backend.repositories.unit_of_work import UnitOfWork


class ArtifactService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def create_artifact(
        self,
        *,
        repository: Repository,
        path: str,
        name: str,
        checksum: str,
        size: int,
        storage_version_id: str,
        artifact_id: UUID | None = None,
    ) -> Artifact:
        values = {
            "repository_id": repository.id,
            "path": path,
            "name": name,
            "checksum": checksum,
            "size": size,
            "storage_version_id": storage_version_id,
        }
        if artifact_id is not None:
            values["id"] = artifact_id

        artifact = await self.uow.artifacts.create(**values)
        await self.uow.commit()
        return artifact

    async def get_artifact(self, artifact_id: UUID) -> Artifact | None:
        return await self.uow.artifacts.get(artifact_id)
