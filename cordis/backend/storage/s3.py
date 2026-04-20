from typing import Any, Protocol

from cordis.backend.storage.errors import (
    StorageAuthorizationError,
    StorageConflictError,
    StorageMultipartStateError,
    StorageObjectNotFoundError,
    StorageProviderError,
    StorageTransientError,
)
from cordis.backend.storage.protocol import StorageAdapter
from cordis.backend.storage.types import (
    CompletedMultipartUpload,
    ObjectMetadata,
    StorageObjectRef,
    UploadedPart,
)


class S3ClientProtocol(Protocol):
    def head_object(self, *, bucket: str, key: str) -> dict[str, Any]: ...

    def put_object(self, *, bucket: str, key: str, body: bytes, checksum: str | None) -> dict[str, Any]: ...

    def delete_object(self, *, bucket: str, key: str) -> None: ...

    def create_presigned_get_url(self, *, bucket: str, key: str, expires_in: int) -> str: ...

    def create_public_object_url(self, *, bucket: str, key: str, version_id: str) -> str: ...

    def ensure_public_prefix_access(self, *, bucket: str, prefix: str) -> bool: ...

    def disable_public_prefix_access(self, *, bucket: str, prefix: str) -> bool: ...

    def create_multipart_upload(self, *, bucket: str, key: str) -> dict[str, Any]: ...

    def upload_part(
        self,
        *,
        bucket: str,
        key: str,
        upload_id: str,
        part_number: int,
        body: bytes,
    ) -> dict[str, Any]: ...

    def complete_multipart_upload(
        self,
        *,
        bucket: str,
        key: str,
        upload_id: str,
        parts: list[dict[str, Any]],
    ) -> dict[str, Any]: ...

    def abort_multipart_upload(self, *, bucket: str, key: str, upload_id: str) -> None: ...


class S3StorageAdapter(StorageAdapter):
    def __init__(self, *, client: S3ClientProtocol, bucket: str, prefix: str = ""):
        self.client = client
        self.bucket = bucket
        self.prefix = prefix.strip("/")

    def stat_object(self, ref: StorageObjectRef) -> ObjectMetadata:
        response = self._call(self.client.head_object, bucket=self.bucket, key=self._build_key(ref))
        return ObjectMetadata(etag=str(response["etag"]), size=int(response["content_length"]))

    def put_object(self, ref: StorageObjectRef, *, body: bytes, checksum: str | None = None) -> str:
        response = self._call(
            self.client.put_object,
            bucket=self.bucket,
            key=self._build_key(ref),
            body=body,
            checksum=checksum,
        )
        return str(response["etag"])

    def delete_object(self, ref: StorageObjectRef) -> None:
        self._call(self.client.delete_object, bucket=self.bucket, key=self._build_key(ref))

    def get_download_url(self, ref: StorageObjectRef, *, expires_in: int) -> str:
        return str(
            self._call(
                self.client.create_presigned_get_url,
                bucket=self.bucket,
                key=self._build_key(ref),
                expires_in=expires_in,
            )
        )

    def get_public_url(self, ref: StorageObjectRef, *, storage_version_id: str) -> str:
        return str(
            self._call(
                self.client.create_public_object_url,
                bucket=self.bucket,
                key=self._build_key(ref),
                version_id=storage_version_id,
            )
        )

    def ensure_repository_public_access(self, *, repository_id: int) -> bool:
        return bool(
            self._call(
                self.client.ensure_public_prefix_access,
                bucket=self.bucket,
                prefix=self._build_repository_prefix(repository_id),
            )
        )

    def disable_repository_public_access(self, *, repository_id: int) -> bool:
        return bool(
            self._call(
                self.client.disable_public_prefix_access,
                bucket=self.bucket,
                prefix=self._build_repository_prefix(repository_id),
            )
        )

    def create_multipart_upload(self, ref: StorageObjectRef) -> str:
        response = self._call(self.client.create_multipart_upload, bucket=self.bucket, key=self._build_key(ref))
        return str(response["upload_id"])

    def upload_part(
        self,
        ref: StorageObjectRef,
        *,
        upload_id: str,
        part_number: int,
        body: bytes,
    ) -> UploadedPart:
        response = self._call(
            self.client.upload_part,
            bucket=self.bucket,
            key=self._build_key(ref),
            upload_id=upload_id,
            part_number=part_number,
            body=body,
        )
        return UploadedPart(part_number=part_number, etag=str(response["etag"]))

    def complete_multipart_upload(
        self,
        ref: StorageObjectRef,
        *,
        upload_id: str,
        parts: list[UploadedPart],
    ) -> CompletedMultipartUpload:
        response = self._call(
            self.client.complete_multipart_upload,
            bucket=self.bucket,
            key=self._build_key(ref),
            upload_id=upload_id,
            parts=[{"part_number": part.part_number, "etag": part.etag} for part in parts],
        )
        version_id = response.get("version_id")
        return CompletedMultipartUpload(
            etag=str(response["etag"]),
            checksum=None,
            version_id=None if version_id is None else str(version_id),
        )

    def abort_multipart_upload(self, ref: StorageObjectRef, *, upload_id: str) -> None:
        self._call(
            self.client.abort_multipart_upload,
            bucket=self.bucket,
            key=self._build_key(ref),
            upload_id=upload_id,
        )

    def _build_key(self, ref: StorageObjectRef) -> str:
        parts = [
            part
            for part in (
                self.prefix,
                f"repositories/{ref.repository_id}",
                f"artifacts/{ref.artifact_id}",
                ref.path.strip("/"),
            )
            if part
        ]
        return "/".join(parts)

    def _build_repository_prefix(self, repository_id: int) -> str:
        parts = [part for part in (self.prefix, f"repositories/{repository_id}") if part]
        return "/".join(parts)

    def _call(self, operation: Any, **kwargs: Any) -> Any:
        try:
            return operation(**kwargs)
        except Exception as error:  # pragma: no cover - exercised via mapping tests
            raise self._translate_provider_error(error) from error

    def _translate_provider_error(self, error: Exception) -> Exception:
        if isinstance(
            error,
            (
                StorageObjectNotFoundError,
                StorageAuthorizationError,
                StorageConflictError,
                StorageMultipartStateError,
                StorageTransientError,
                StorageProviderError,
            ),
        ):
            return error

        response = getattr(error, "response", None)
        if isinstance(response, dict):
            error_data = response.get("Error", {})
            if isinstance(error_data, dict) and "Code" in error_data:
                code = str(error_data["Code"])
            else:
                code = error.__class__.__name__
        else:
            code = getattr(error, "code", error.__class__.__name__)
        if code in {"NoSuchKey", "NotFound", "NoSuchObject"}:
            return StorageObjectNotFoundError()
        if code in {"AccessDenied", "InvalidAccessKeyId", "SignatureDoesNotMatch", "403"}:
            return StorageAuthorizationError()
        if code in {"Conflict", "PreconditionFailed", "EntityAlreadyExists", "BucketAlreadyOwnedByYou"}:
            return StorageConflictError()
        if code in {"InvalidPart", "InvalidPartOrder", "NoSuchUpload"}:
            return StorageMultipartStateError()
        if code in {"SlowDown", "ServiceUnavailable", "RequestTimeout", "InternalError", "500", "503"}:
            return StorageTransientError()
        if code in {"NoSuchBucket", "404"}:
            return StorageObjectNotFoundError()
        return StorageProviderError()
