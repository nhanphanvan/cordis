from dataclasses import dataclass
from pathlib import PurePosixPath
from uuid import UUID

from cordis.backend.exceptions import AppStatus, ConflictError, NotFoundError, NotUniqueError, UnprocessableEntityError
from cordis.backend.models import Artifact, Repository, Version
from cordis.backend.repositories.unit_of_work import UnitOfWork
from cordis.backend.schemas.requests.artifact import (
    ArtifactCreateRequest,
    ResourceCheckRequest,
    VersionArtifactCreateRequest,
)

from .base import BaseValidator


@dataclass(slots=True)
class ValidatedArtifactInput:
    repository: Repository
    normalized_path: str
    name: str
    checksum: str
    size: int


class ArtifactCreateValidator(BaseValidator):
    @classmethod
    async def validate(cls, *, uow: UnitOfWork, request: ArtifactCreateRequest) -> ValidatedArtifactInput:
        repository = await uow.repositories.get(request.repository_id)
        if repository is None:
            raise NotFoundError("Repository not found", app_status=AppStatus.ERROR_REPOSITORY_NOT_FOUND)
        if request.size < 0:
            raise UnprocessableEntityError("Artifact size must be non-negative", app_status=AppStatus.ERROR_VALIDATION)
        normalized_path = request.path.strip("/")
        if not normalized_path:
            raise UnprocessableEntityError(
                "Artifact path must not be empty",
                app_status=AppStatus.ERROR_ARTIFACT_PATH_INVALID,
            )
        existing = await uow.artifacts.get_by_repository_and_path(
            repository_id=request.repository_id,
            path=normalized_path,
        )
        if existing is not None:
            raise NotUniqueError(
                "Artifact path already exists in repository",
                app_status=AppStatus.ERROR_ARTIFACT_PATH_ALREADY_EXISTS,
            )
        name = PurePosixPath(normalized_path).name
        if not name:
            raise UnprocessableEntityError(
                "Artifact path must include a file name",
                app_status=AppStatus.ERROR_ARTIFACT_PATH_INVALID,
            )
        return ValidatedArtifactInput(
            repository=repository,
            normalized_path=normalized_path,
            name=name,
            checksum=request.checksum,
            size=request.size,
        )


class ArtifactReadValidator(BaseValidator):
    @classmethod
    async def validate(cls, *, uow: UnitOfWork, artifact_id: UUID) -> Artifact:
        artifact = await uow.artifacts.get(artifact_id)
        if artifact is None:
            raise NotFoundError("Artifact not found", app_status=AppStatus.ERROR_ARTIFACT_NOT_FOUND)
        return artifact


class VersionArtifactAttachValidator(BaseValidator):
    @classmethod
    async def validate(
        cls,
        *,
        uow: UnitOfWork,
        version: Version,
        request: VersionArtifactCreateRequest,
    ) -> Artifact:
        artifact = await uow.artifacts.get(request.artifact_id)
        if artifact is None:
            raise NotFoundError("Artifact not found", app_status=AppStatus.ERROR_ARTIFACT_NOT_FOUND)
        if artifact.repository_id != version.repository_id:
            raise UnprocessableEntityError(
                "Artifact does not belong to version repository",
                app_status=AppStatus.ERROR_ARTIFACT_REPOSITORY_MISMATCH,
            )
        existing = await uow.version_artifacts.get_for_version_and_path(version_id=version.id, path=artifact.path)
        if existing is not None:
            if existing.artifact_id == artifact.id:
                return artifact
            raise ConflictError(
                "Artifact path already exists in version",
                app_status=AppStatus.ERROR_ARTIFACT_VERSION_PATH_CONFLICT,
            )
        return artifact


class ResourceCheckValidator(BaseValidator):
    @classmethod
    async def validate(cls, *, uow: UnitOfWork, request: ResourceCheckRequest) -> Version:
        version = await uow.versions.get(request.version_id)
        if version is None:
            raise NotFoundError("Version not found", app_status=AppStatus.ERROR_VERSION_NOT_FOUND)
        return version
