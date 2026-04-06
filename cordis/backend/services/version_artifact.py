from uuid import UUID

from cordis.backend.models import Artifact, Version
from cordis.backend.repositories.unit_of_work import UnitOfWork


class VersionArtifactService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def attach_artifact(self, *, version: Version, artifact: Artifact) -> Artifact:
        existing_for_path = await self.uow.version_artifacts.get_for_version_and_path(
            version_id=version.id,
            path=artifact.path,
        )
        if existing_for_path is not None and existing_for_path.artifact_id == artifact.id:
            return existing_for_path.artifact
        await self.uow.version_artifacts.create(version_id=version.id, artifact_id=artifact.id)
        await self.uow.commit()
        return artifact

    async def list_for_version(self, version: Version) -> list[Artifact]:
        associations = await self.uow.version_artifacts.list_for_version(version.id)
        return [association.artifact for association in associations]

    async def check_resource(
        self,
        *,
        version_id: UUID,
        path: str,
        checksum: str,
        size: int,
    ) -> tuple[str, UUID | None]:
        association = await self.uow.version_artifacts.get_for_version_and_path(
            version_id=version_id,
            path=path.strip("/"),
        )
        if association is None:
            return "missing", None

        artifact = association.artifact
        if artifact.checksum == checksum and artifact.size == size:
            return "exists", artifact.id
        return "conflict", artifact.id
