from typing import cast

from cordis.backend.exceptions import AppStatus, ConflictError, NotFoundError, UnprocessableEntityError
from cordis.backend.models import Artifact, Version
from cordis.backend.repositories.unit_of_work import UnitOfWork


class VersionArtifactService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def attach_artifact(self, *, version_id: str, artifact_id: str) -> Artifact:
        version = await self._get_version(version_id)
        artifact = await self._get_artifact(artifact_id)
        if artifact.repository_id != version.repository_id:
            raise UnprocessableEntityError(
                "Artifact does not belong to version repository",
                app_status=AppStatus.ERROR_ARTIFACT_REPOSITORY_MISMATCH,
            )

        existing_for_path = await self.uow.version_artifacts.get_for_version_and_path(
            version_id=version_id,
            path=artifact.path,
        )
        if existing_for_path is not None:
            if existing_for_path.artifact_id == artifact_id:
                return cast(Artifact, existing_for_path.artifact)
            raise ConflictError(
                "Artifact path already exists in version",
                app_status=AppStatus.ERROR_ARTIFACT_VERSION_PATH_CONFLICT,
            )

        await self.uow.version_artifacts.create(version_id=version_id, artifact_id=artifact_id)
        await self.uow.commit()
        return artifact

    async def list_for_version(self, version_id: str) -> list[Artifact]:
        await self._get_version(version_id)
        associations = await self.uow.version_artifacts.list_for_version(version_id)
        return [association.artifact for association in associations]

    async def check_resource(
        self,
        *,
        version_id: str,
        path: str,
        checksum: str,
        size: int,
    ) -> tuple[str, str | None]:
        await self._get_version(version_id)
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

    async def _get_version(self, version_id: str) -> Version:
        version = await self.uow.versions.get(version_id)
        if version is None:
            raise NotFoundError("Version not found", app_status=AppStatus.ERROR_VERSION_NOT_FOUND)
        return version

    async def _get_artifact(self, artifact_id: str) -> Artifact:
        artifact = await self.uow.artifacts.get(artifact_id)
        if artifact is None:
            raise NotFoundError("Artifact not found", app_status=AppStatus.ERROR_ARTIFACT_NOT_FOUND)
        return artifact
