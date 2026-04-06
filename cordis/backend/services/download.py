import logging
from uuid import UUID

from cordis.backend.config import build_config
from cordis.backend.models import Artifact
from cordis.backend.repositories.unit_of_work import UnitOfWork
from cordis.backend.storage import StorageObjectRef
from cordis.backend.storage import factory as storage_factory

logger = logging.getLogger(__name__)


class DownloadService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def get_download_url(self, *, version_id: UUID, artifact: Artifact) -> tuple[str, int]:
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
            artifact.id,
            artifact.repository_id,
        )
        return url, expires_in
