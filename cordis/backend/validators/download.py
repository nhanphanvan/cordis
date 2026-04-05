from typing import cast

from cordis.backend.exceptions import AppStatus, NotFoundError
from cordis.backend.models import Artifact, Version
from cordis.backend.repositories.unit_of_work import UnitOfWork

from .base import BaseValidator


class VersionArtifactPathReadValidator(BaseValidator):
    @classmethod
    async def validate(cls, *, uow: UnitOfWork, version: Version, path: str) -> Artifact:
        association = await uow.version_artifacts.get_for_version_and_path(version_id=version.id, path=path.strip("/"))
        if association is None:
            raise NotFoundError("Artifact not found in version", app_status=AppStatus.ERROR_ARTIFACT_NOT_FOUND)
        return cast(Artifact, association.artifact)


class VersionArtifactReadValidator(BaseValidator):
    @classmethod
    async def validate(cls, *, uow: UnitOfWork, version: Version, artifact_id: str) -> Artifact:
        association = await uow.version_artifacts.get_for_version_and_artifact(
            version_id=version.id,
            artifact_id=artifact_id,
        )
        if association is None:
            raise NotFoundError("Artifact not found in version", app_status=AppStatus.ERROR_ARTIFACT_NOT_FOUND)
        return cast(Artifact, association.artifact)
