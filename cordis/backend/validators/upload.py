from dataclasses import dataclass
from pathlib import PurePosixPath
from uuid import UUID

from cordis.backend.exceptions import AppStatus, ConflictError, NotFoundError, UnprocessableEntityError
from cordis.backend.models import Artifact, UploadSession, UploadSessionPart, Version
from cordis.backend.repositories.unit_of_work import UnitOfWork
from cordis.backend.schemas.requests.upload import UploadSessionCreateRequest

from .base import BaseValidator

TERMINAL_UPLOAD_STATUSES = {"completed", "failed", "aborted"}


@dataclass(slots=True)
class ValidatedUploadCreate:
    version: Version
    normalized_path: str
    name: str
    checksum: str
    size: int


class UploadSessionCreateValidator(BaseValidator):
    @classmethod
    async def validate(cls, *, uow: UnitOfWork, request: UploadSessionCreateRequest) -> ValidatedUploadCreate:
        version = await uow.versions.get(request.version_id)
        if version is None:
            raise NotFoundError("Version not found", app_status=AppStatus.ERROR_VERSION_NOT_FOUND)
        if request.size < 0:
            raise UnprocessableEntityError(
                "Upload size must be non-negative",
                app_status=AppStatus.ERROR_UPLOAD_SIZE_INVALID,
            )
        normalized_path = request.path.strip("/")
        if not normalized_path:
            raise UnprocessableEntityError(
                "Upload path must not be empty",
                app_status=AppStatus.ERROR_UPLOAD_PATH_INVALID,
            )
        name = PurePosixPath(normalized_path).name
        if not name:
            raise UnprocessableEntityError(
                "Upload path must include a file name",
                app_status=AppStatus.ERROR_UPLOAD_PATH_INVALID,
            )
        association = await uow.version_artifacts.get_for_version_and_path(
            version_id=request.version_id,
            path=normalized_path,
        )
        if association is not None:
            artifact = association.artifact
            if artifact.checksum == request.checksum and artifact.size == request.size:
                raise ConflictError(
                    "Artifact already exists in version",
                    app_status=AppStatus.ERROR_ARTIFACT_ALREADY_EXISTS_IN_VERSION,
                )
            raise ConflictError(
                "Artifact path already exists in version with different metadata",
                app_status=AppStatus.ERROR_ARTIFACT_VERSION_METADATA_CONFLICT,
            )
        return ValidatedUploadCreate(
            version=version,
            normalized_path=normalized_path,
            name=name,
            checksum=request.checksum,
            size=request.size,
        )


class UploadSessionReadValidator(BaseValidator):
    @classmethod
    async def validate(cls, *, uow: UnitOfWork, session_id: UUID) -> tuple[UploadSession, list[UploadSessionPart]]:
        session = await uow.upload_sessions.get(session_id)
        if session is None:
            raise NotFoundError("Upload session not found", app_status=AppStatus.ERROR_UPLOAD_SESSION_NOT_FOUND)
        parts = await uow.upload_session_parts.list_for_session(session_id)
        return session, parts


class UploadSessionMutableValidator(BaseValidator):
    @classmethod
    async def validate(cls, *, session: UploadSession) -> UploadSession:
        if session.status in TERMINAL_UPLOAD_STATUSES:
            raise ConflictError(
                "Upload session is already terminal",
                app_status=AppStatus.ERROR_UPLOAD_SESSION_TERMINAL,
            )
        return session


class UploadSessionCompletionValidator(BaseValidator):
    @classmethod
    async def validate(
        cls,
        *,
        session: UploadSession,
        parts: list[UploadSessionPart],
    ) -> tuple[UploadSession, list[UploadSessionPart]]:
        await UploadSessionMutableValidator.validate(session=session)
        if not parts:
            raise UnprocessableEntityError(
                "Upload session has no uploaded parts",
                app_status=AppStatus.ERROR_UPLOAD_SESSION_NO_PARTS,
            )
        return session, parts


class ArtifactResolutionValidator(BaseValidator):
    @classmethod
    async def validate(
        cls,
        *,
        uow: UnitOfWork,
        repository_id: int,
        artifact_id: UUID | None,
        path: str,
        checksum: str,
        size: int,
    ) -> Artifact | None:
        _ = artifact_id
        existing = await uow.artifacts.get_by_repository_and_path(repository_id=repository_id, path=path.strip("/"))
        if existing is not None:
            if existing.checksum == checksum and existing.size == size:
                return existing
            raise ConflictError(
                "Artifact path already exists in repository with different metadata",
                app_status=AppStatus.ERROR_ARTIFACT_CHECKSUM_CONFLICT,
            )
        return None
