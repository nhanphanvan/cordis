from datetime import timedelta
from io import BytesIO
from typing import Any

from minio import Minio
from minio.datatypes import Part
from minio.error import InvalidResponseError, S3Error, ServerError
from minio.versioningconfig import VersioningConfig

from cordis.backend.storage.errors import (
    StorageAuthorizationError,
    StorageConflictError,
    StorageMultipartStateError,
    StorageObjectNotFoundError,
    StorageProviderError,
    StorageTransientError,
)

MINIO_VERSIONING_ENABLED = "Enabled"


def translate_minio_error(error: Exception) -> Exception:
    if isinstance(error, (StorageObjectNotFoundError, StorageAuthorizationError, StorageConflictError)):
        return error
    if isinstance(error, (StorageMultipartStateError, StorageProviderError, StorageTransientError)):
        return error

    if isinstance(error, (ServerError, InvalidResponseError)):
        return StorageTransientError()

    code = getattr(error, "code", error.__class__.__name__)
    if code in {"NoSuchKey", "NotFound", "NoSuchObject", "NoSuchBucket"}:
        return StorageObjectNotFoundError()
    if code in {"AccessDenied", "InvalidAccessKeyId", "SignatureDoesNotMatch"}:
        return StorageAuthorizationError()
    if code in {"Conflict", "PreconditionFailed", "EntityAlreadyExists", "BucketAlreadyOwnedByYou"}:
        return StorageConflictError()
    if code in {"InvalidPart", "InvalidPartOrder", "NoSuchUpload"}:
        return StorageMultipartStateError()
    if code in {"SlowDown", "ServiceUnavailable", "RequestTimeout", "InternalError"}:
        return StorageTransientError()
    if isinstance(error, S3Error) and error.code is None:
        return StorageProviderError()
    return StorageProviderError()


class MinioStorageClient:
    def __init__(self, client: Minio):
        self.client = client

    def ensure_bucket_exists(self, *, bucket: str, region: str | None) -> bool:
        try:
            exists = self.client.bucket_exists(bucket)
            if not exists:
                self.client.make_bucket(bucket, location=region)
            return not exists
        except Exception as error:  # pragma: no cover - exercised via mapping tests
            raise translate_minio_error(error) from error

    def ensure_bucket_versioning_enabled(self, *, bucket: str) -> bool:
        try:
            versioning = self.client.get_bucket_versioning(bucket)
            if getattr(versioning, "status", None) == MINIO_VERSIONING_ENABLED:
                return False
            self.client.set_bucket_versioning(bucket, VersioningConfig(status=MINIO_VERSIONING_ENABLED))
            return True
        except Exception as error:  # pragma: no cover - exercised via mapping tests
            raise translate_minio_error(error) from error

    def head_object(self, *, bucket: str, key: str) -> dict[str, Any]:
        result = self.client.stat_object(bucket, key)
        return {"etag": str(result.etag), "content_length": int(result.size or 0)}

    def put_object(self, *, bucket: str, key: str, body: bytes, checksum: str | None) -> dict[str, Any]:
        _ = checksum
        result = self.client.put_object(
            bucket,
            key,
            BytesIO(body),
            length=len(body),
            content_type="application/octet-stream",
        )
        return {
            "etag": None if result.etag is None else str(result.etag),
            "version_id": None if result.version_id is None else str(result.version_id),
        }

    def delete_object(self, *, bucket: str, key: str) -> None:
        self.client.remove_object(bucket, key)

    def create_presigned_get_url(self, *, bucket: str, key: str, expires_in: int) -> str:
        return str(self.client.presigned_get_object(bucket, key, expires=timedelta(seconds=expires_in)))

    def create_multipart_upload(self, *, bucket: str, key: str) -> dict[str, Any]:
        upload_id = self.client._create_multipart_upload(bucket, key, headers={})  # pylint: disable=protected-access
        return {"upload_id": str(upload_id)}

    def upload_part(
        self,
        *,
        bucket: str,
        key: str,
        upload_id: str,
        part_number: int,
        body: bytes,
    ) -> dict[str, Any]:
        etag = self.client._upload_part(  # pylint: disable=protected-access
            bucket,
            key,
            body,
            None,
            upload_id,
            part_number,
        )
        return {"etag": str(etag)}

    def complete_multipart_upload(
        self,
        *,
        bucket: str,
        key: str,
        upload_id: str,
        parts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        result = self.client._complete_multipart_upload(  # pylint: disable=protected-access
            bucket,
            key,
            upload_id,
            [Part(part_number=part["part_number"], etag=part["etag"]) for part in parts],
        )
        return {
            "etag": str(result.etag),
            "version_id": None if result.version_id is None else str(result.version_id),
        }

    def abort_multipart_upload(self, *, bucket: str, key: str, upload_id: str) -> None:
        self.client._abort_multipart_upload(bucket, key, upload_id)  # pylint: disable=protected-access
