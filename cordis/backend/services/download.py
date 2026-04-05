import logging
from typing import cast

from cordis.backend.config import build_config
from cordis.backend.exceptions import AppStatus, NotFoundError
from cordis.backend.models import Artifact
from cordis.backend.repositories.unit_of_work import UnitOfWork
from cordis.backend.storage import StorageObjectRef
from cordis.backend.storage import factory as storage_factory

logger = logging.getLogger(__name__)


class DownloadService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def get_artifact_for_version_by_path(self, *, version_id: str, path: str) -> Artifact:
        association = await self.uow.version_artifacts.get_for_version_and_path(
            version_id=version_id,
            path=path.strip("/"),
        )
        if association is None:
            raise NotFoundError("Artifact not found in version", app_status=AppStatus.ERROR_ARTIFACT_NOT_FOUND)
        return cast(Artifact, association.artifact)

    async def get_artifact_for_version(self, *, version_id: str, artifact_id: str) -> Artifact:
        association = await self.uow.version_artifacts.get_for_version_and_artifact(
            version_id=version_id,
            artifact_id=artifact_id,
        )
        if association is None:
            raise NotFoundError("Artifact not found in version", app_status=AppStatus.ERROR_ARTIFACT_NOT_FOUND)
        return cast(Artifact, association.artifact)

    async def get_download_url(self, *, version_id: str, artifact_id: str) -> tuple[str, int]:
        artifact = await self.get_artifact_for_version(version_id=version_id, artifact_id=artifact_id)
        expires_in = build_config().storage.presign_expiry_seconds
        url = storage_factory.get_storage_adapter().get_download_url(
            StorageObjectRef(
                repository_id=artifact.repository_id,
                artifact_id=artifact.id,
                path=artifact.path,
            ),
            expires_in=expires_in,
        )
        logger.info(
            "Download URL generated version_id=%s artifact_id=%s repository_id=%s",
            version_id,
            artifact_id,
            artifact.repository_id,
        )
        return url, expires_in
