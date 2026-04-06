import logging

from cordis.backend.exceptions import AppStatus, ConflictError, InternalServerError
from cordis.backend.models import Repository, UploadSession, UploadSessionPart
from cordis.backend.models.version import Version
from cordis.backend.repositories.unit_of_work import UnitOfWork
from cordis.backend.services.artifact import ArtifactService
from cordis.backend.services.version_artifact import VersionArtifactService
from cordis.backend.storage import CompletedMultipartUpload, StorageMultipartStateError, StorageObjectRef, UploadedPart
from cordis.backend.storage import factory as storage_factory
from cordis.backend.validators.upload import ArtifactResolutionValidator

logger = logging.getLogger(__name__)


class UploadService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def create_or_resume_session(
        self,
        *,
        version: Version,
        path: str,
        checksum: str,
        size: int,
    ) -> tuple[UploadSession, bool]:
        normalized_path = path.strip("/")

        resumable = await self.uow.upload_sessions.get_resumable(
            version_id=version.id,
            path=normalized_path,
            checksum=checksum,
            size=size,
        )
        if resumable is not None:
            logger.info(
                "Upload session resumed session_id=%s version_id=%s path=%s",
                resumable.id,
                version.id,
                normalized_path,
            )
            return resumable, False

        session = await self.uow.upload_sessions.create(
            repository_id=version.repository_id,
            version_id=version.id,
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
            version.id,
            normalized_path,
        )
        return session, True

    async def upload_part(
        self,
        *,
        session: UploadSession,
        part_number: int,
        content_bytes: bytes,
    ) -> tuple[UploadSession, list[UploadSessionPart]]:
        uploaded_part = storage_factory.get_storage_adapter().upload_part(
            self._storage_ref(session),
            upload_id=session.upload_id,
            part_number=part_number,
            body=content_bytes,
        )
        existing = await self.uow.upload_session_parts.get_for_session_and_part_number(
            session_id=session.id,
            part_number=part_number,
        )
        if existing is None:
            await self.uow.upload_session_parts.create(
                session_id=session.id,
                part_number=uploaded_part.part_number,
                etag=uploaded_part.etag,
            )
        else:
            existing.etag = uploaded_part.etag
            await self.uow.flush()
        session.status = "in_progress"
        session.error_message = None
        await self.uow.commit()
        parts = await self.uow.upload_session_parts.list_for_session(session.id)
        logger.info("Upload part stored session_id=%s part_number=%s", session.id, part_number)
        return session, parts

    async def complete_session(
        self,
        *,
        session: UploadSession,
        parts: list[UploadSessionPart],
        version: Version,
        repository: Repository,
    ) -> tuple[UploadSession, list[UploadSessionPart]]:
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
            logger.error("Upload session failed session_id=%s reason=multipart_state_invalid", session.id)
            raise

        if completed.etag != session.checksum:
            session.status = "failed"
            session.error_message = "Checksum mismatch"
            await self.uow.commit()
            logger.error("Upload session failed session_id=%s reason=checksum_mismatch", session.id)
            raise ConflictError(
                "Completed upload checksum does not match expected checksum",
                app_status=AppStatus.ERROR_UPLOAD_CHECKSUM_MISMATCH,
            )
        if completed.version_id is None:
            session.status = "failed"
            session.error_message = "Storage version ID missing"
            await self.uow.commit()
            logger.error("Upload session failed session_id=%s reason=storage_version_id_missing", session.id)
            raise InternalServerError(
                "Storage version ID missing",
                app_status=AppStatus.ERROR_STORAGE_VERSION_ID_MISSING,
            )

        artifact = await ArtifactResolutionValidator.validate(
            uow=self.uow,
            repository_id=session.repository_id,
            artifact_id=session.artifact_id,
            path=session.path,
            checksum=session.checksum,
            size=session.size,
        )
        if artifact is None:
            artifact = await ArtifactService(self.uow).create_artifact(
                repository=repository,
                path=session.path,
                name=session.path.rsplit("/", maxsplit=1)[-1],
                checksum=session.checksum,
                size=session.size,
                storage_version_id=completed.version_id,
                artifact_id=session.artifact_id,
            )
        await VersionArtifactService(self.uow).attach_artifact(version=version, artifact=artifact)
        session.artifact_id = artifact.id
        session.status = "completed"
        session.error_message = None
        await self.uow.commit()
        refreshed_parts = await self.uow.upload_session_parts.list_for_session(session.id)
        logger.info("Upload session completed session_id=%s artifact_id=%s", session.id, artifact.id)
        return session, refreshed_parts

    async def abort_session(self, session: UploadSession) -> tuple[UploadSession, list[UploadSessionPart]]:
        if session.status == "aborted":
            parts = await self.uow.upload_session_parts.list_for_session(session.id)
            return session, parts
        if session.status == "completed":
            raise ConflictError(
                "Upload session is already terminal",
                app_status=AppStatus.ERROR_UPLOAD_SESSION_TERMINAL,
            )
        storage_factory.get_storage_adapter().abort_multipart_upload(
            self._storage_ref(session),
            upload_id=session.upload_id,
        )
        session.status = "aborted"
        session.error_message = None
        await self.uow.commit()
        parts = await self.uow.upload_session_parts.list_for_session(session.id)
        logger.info("Upload session aborted session_id=%s", session.id)
        return session, parts

    def _storage_ref(self, session: UploadSession) -> StorageObjectRef:
        return StorageObjectRef(
            repository_id=session.repository_id,
            artifact_id=session.artifact_id,
            path=session.path,
        )
