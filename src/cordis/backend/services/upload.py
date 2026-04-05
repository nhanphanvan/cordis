import logging

from cordis.backend.errors import ConflictError, NotFoundError, ValidationError
from cordis.backend.models import UploadSession, UploadSessionPart
from cordis.backend.repositories.unit_of_work import UnitOfWork
from cordis.backend.services.artifact import ArtifactService
from cordis.backend.services.version import VersionService
from cordis.backend.services.version_artifact import VersionArtifactService
from cordis.backend.storage import (
    CompletedMultipartUpload,
    StorageMultipartStateError,
    StorageObjectRef,
    UploadedPart,
)
from cordis.backend.storage import factory as storage_factory

TERMINAL_UPLOAD_STATUSES = {"completed", "failed", "aborted"}
logger = logging.getLogger(__name__)


class UploadService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def create_or_resume_session(
        self,
        *,
        version_id: str,
        path: str,
        checksum: str,
        size: int,
    ) -> tuple[UploadSession, bool]:
        version = await VersionService(self.uow).get_version(version_id)
        normalized_path = path.strip("/")
        if size < 0:
            raise ValidationError("Upload size must be non-negative")
        if not normalized_path:
            raise ValidationError("Upload path must not be empty")

        existing_status, _ = await VersionArtifactService(self.uow).check_resource(
            version_id=version_id,
            path=normalized_path,
            checksum=checksum,
            size=size,
        )
        if existing_status == "exists":
            raise ConflictError("Artifact already exists in version")
        if existing_status == "conflict":
            raise ConflictError("Artifact path already exists in version with different metadata")

        resumable = await self.uow.upload_sessions.get_resumable(
            version_id=version_id,
            path=normalized_path,
            checksum=checksum,
            size=size,
        )
        if resumable is not None:
            logger.info(
                "Upload session resumed session_id=%s version_id=%s path=%s",
                resumable.id,
                version_id,
                normalized_path,
            )
            return resumable, False

        session = await self.uow.upload_sessions.create(
            repository_id=version.repository_id,
            version_id=version_id,
            path=normalized_path,
            checksum=checksum,
            size=size,
            upload_id="pending",
            status="created",
            error_message=None,
        )
        session_ref = self._storage_ref(session)
        session.upload_id = storage_factory.get_storage_adapter().create_multipart_upload(session_ref)
        await self.uow.commit()
        logger.info(
            "Upload session created session_id=%s version_id=%s path=%s",
            session.id,
            version_id,
            normalized_path,
        )
        return session, True

    async def get_session(self, session_id: str) -> tuple[UploadSession, list[UploadSessionPart]]:
        session = await self.uow.upload_sessions.get(session_id)
        if session is None:
            raise NotFoundError("Upload session not found")
        parts = await self.uow.upload_session_parts.list_for_session(session_id)
        return session, parts

    async def upload_part(
        self,
        *,
        session_id: str,
        part_number: int,
        content_bytes: bytes,
    ) -> tuple[UploadSession, list[UploadSessionPart]]:
        session, _ = await self.get_session(session_id)
        if session.status in TERMINAL_UPLOAD_STATUSES:
            raise ConflictError("Upload session is already terminal")

        uploaded_part = storage_factory.get_storage_adapter().upload_part(
            self._storage_ref(session),
            upload_id=session.upload_id,
            part_number=part_number,
            body=content_bytes,
        )
        existing = await self.uow.upload_session_parts.get_for_session_and_part_number(
            session_id=session_id,
            part_number=part_number,
        )
        if existing is None:
            await self.uow.upload_session_parts.create(
                session_id=session_id,
                part_number=uploaded_part.part_number,
                etag=uploaded_part.etag,
            )
        else:
            existing.etag = uploaded_part.etag
            await self.uow.flush()
        session.status = "in_progress"
        session.error_message = None
        await self.uow.commit()
        logger.info("Upload part stored session_id=%s part_number=%s", session_id, part_number)
        return await self.get_session(session_id)

    async def complete_session(self, session_id: str) -> tuple[UploadSession, list[UploadSessionPart]]:
        session, parts = await self.get_session(session_id)
        if session.status in TERMINAL_UPLOAD_STATUSES:
            raise ConflictError("Upload session is already terminal")
        if not parts:
            raise ValidationError("Upload session has no uploaded parts")

        session.status = "finalizing"
        await self.uow.flush()
        storage = storage_factory.get_storage_adapter()
        try:
            completed: CompletedMultipartUpload = storage.complete_multipart_upload(
                self._storage_ref(session),
                upload_id=session.upload_id,
                parts=[UploadedPart(part_number=part.part_number, etag=part.etag) for part in parts],
            )
        except StorageMultipartStateError:
            session.status = "failed"
            session.error_message = "Multipart state invalid"
            await self.uow.commit()
            logger.error("Upload session failed session_id=%s reason=multipart_state_invalid", session_id)
            raise

        if completed.etag != session.checksum:
            session.status = "failed"
            session.error_message = "Checksum mismatch"
            await self.uow.commit()
            logger.error("Upload session failed session_id=%s reason=checksum_mismatch", session_id)
            raise ConflictError("Completed upload checksum does not match expected checksum")

        artifact = await ArtifactService(self.uow).resolve_or_create_artifact(
            repository_id=session.repository_id,
            artifact_id=session.artifact_id,
            path=session.path,
            checksum=session.checksum,
            size=session.size,
        )
        await VersionArtifactService(self.uow).attach_artifact(version_id=session.version_id, artifact_id=artifact.id)
        session.artifact_id = artifact.id
        session.status = "completed"
        session.error_message = None
        await self.uow.commit()
        logger.info("Upload session completed session_id=%s artifact_id=%s", session_id, artifact.id)
        return await self.get_session(session_id)

    async def abort_session(self, session_id: str) -> tuple[UploadSession, list[UploadSessionPart]]:
        session, _ = await self.get_session(session_id)
        if session.status == "aborted":
            return await self.get_session(session_id)
        if session.status == "completed":
            raise ConflictError("Completed upload session cannot be aborted")
        storage_factory.get_storage_adapter().abort_multipart_upload(
            self._storage_ref(session),
            upload_id=session.upload_id,
        )
        session.status = "aborted"
        session.error_message = None
        await self.uow.commit()
        logger.info("Upload session aborted session_id=%s", session_id)
        return await self.get_session(session_id)

    def _storage_ref(self, session: UploadSession) -> StorageObjectRef:
        return StorageObjectRef(
            repository_id=session.repository_id,
            artifact_id=session.artifact_id,
            path=session.path,
        )
