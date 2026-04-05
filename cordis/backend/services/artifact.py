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
        artifact_id: str | None = None,
    ) -> Artifact:
        values = {
            "repository_id": repository.id,
            "path": path,
            "name": name,
            "checksum": checksum,
            "size": size,
        }
        if artifact_id is not None:
            values["id"] = artifact_id

        artifact = await self.uow.artifacts.create(**values)
        await self.uow.commit()
        return artifact

    async def get_artifact(self, artifact_id: str) -> Artifact | None:
        return await self.uow.artifacts.get(artifact_id)
