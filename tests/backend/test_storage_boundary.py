from typing import Any

import pytest

from cordis.backend.storage import (
    CompletedMultipartUpload,
    ObjectMetadata,
    S3StorageAdapter,
    StorageAuthorizationError,
    StorageConflictError,
    StorageMultipartStateError,
    StorageObjectNotFoundError,
    StorageObjectRef,
    StorageProviderError,
    StorageTransientError,
    UploadedPart,
)


class FakeProviderError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class FakeS3Client:
    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []
        self.mode = "ok"

    def head_object(self, *, bucket: str, key: str) -> dict[str, Any]:
        self.calls.append(("head_object", bucket, key))
        if self.mode != "ok":
            raise FakeProviderError(self.mode)
        return {"etag": "sha256:abc123", "content_length": 1024}

    def put_object(self, *, bucket: str, key: str, body: bytes, checksum: str | None) -> dict[str, Any]:
        self.calls.append(("put_object", bucket, key, body, checksum))
        if self.mode != "ok":
            raise FakeProviderError(self.mode)
        return {"etag": checksum or "generated"}

    def delete_object(self, *, bucket: str, key: str) -> None:
        self.calls.append(("delete_object", bucket, key))
        if self.mode != "ok":
            raise FakeProviderError(self.mode)

    def create_presigned_get_url(self, *, bucket: str, key: str, expires_in: int) -> str:
        self.calls.append(("create_presigned_get_url", bucket, key, expires_in))
        if self.mode != "ok":
            raise FakeProviderError(self.mode)
        return f"https://example.invalid/{bucket}/{key}?expires={expires_in}"

    def create_multipart_upload(self, *, bucket: str, key: str) -> dict[str, Any]:
        self.calls.append(("create_multipart_upload", bucket, key))
        if self.mode != "ok":
            raise FakeProviderError(self.mode)
        return {"upload_id": "upload-123"}

    def upload_part(
        self,
        *,
        bucket: str,
        key: str,
        upload_id: str,
        part_number: int,
        body: bytes,
    ) -> dict[str, Any]:
        self.calls.append(("upload_part", bucket, key, upload_id, part_number, body))
        if self.mode != "ok":
            raise FakeProviderError(self.mode)
        return {"etag": f"etag-{part_number}"}

    def complete_multipart_upload(
        self,
        *,
        bucket: str,
        key: str,
        upload_id: str,
        parts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        self.calls.append(("complete_multipart_upload", bucket, key, upload_id, parts))
        if self.mode != "ok":
            raise FakeProviderError(self.mode)
        return {"etag": "complete-etag", "version_id": "version-1"}

    def abort_multipart_upload(self, *, bucket: str, key: str, upload_id: str) -> None:
        self.calls.append(("abort_multipart_upload", bucket, key, upload_id))
        if self.mode != "ok":
            raise FakeProviderError(self.mode)


def _artifact_ref() -> StorageObjectRef:
    return StorageObjectRef(repository_id=42, artifact_id="artifact-123", path="models/weights.bin")


def test_s3_storage_adapter_builds_object_keys_and_maps_object_operations() -> None:
    client = FakeS3Client()
    adapter = S3StorageAdapter(client=client, bucket="cordis-artifacts", prefix="tenant-a")
    ref = _artifact_ref()

    metadata = adapter.stat_object(ref)
    upload_etag = adapter.put_object(ref, body=b"payload", checksum="sha256:abc123")
    download_url = adapter.get_download_url(ref, expires_in=900)
    adapter.delete_object(ref)

    assert metadata == ObjectMetadata(etag="sha256:abc123", size=1024)
    assert upload_etag == "sha256:abc123"
    assert download_url == (
        "https://example.invalid/cordis-artifacts/"
        "tenant-a/repositories/42/artifacts/artifact-123/models/weights.bin?expires=900"
    )
    assert client.calls == [
        (
            "head_object",
            "cordis-artifacts",
            "tenant-a/repositories/42/artifacts/artifact-123/models/weights.bin",
        ),
        (
            "put_object",
            "cordis-artifacts",
            "tenant-a/repositories/42/artifacts/artifact-123/models/weights.bin",
            b"payload",
            "sha256:abc123",
        ),
        (
            "create_presigned_get_url",
            "cordis-artifacts",
            "tenant-a/repositories/42/artifacts/artifact-123/models/weights.bin",
            900,
        ),
        (
            "delete_object",
            "cordis-artifacts",
            "tenant-a/repositories/42/artifacts/artifact-123/models/weights.bin",
        ),
    ]


def test_s3_storage_adapter_exposes_multipart_primitives() -> None:
    client = FakeS3Client()
    adapter = S3StorageAdapter(client=client, bucket="cordis-artifacts", prefix="")
    ref = _artifact_ref()

    upload_id = adapter.create_multipart_upload(ref)
    part = adapter.upload_part(ref, upload_id=upload_id, part_number=1, body=b"chunk")
    completed = adapter.complete_multipart_upload(ref, upload_id=upload_id, parts=[part])
    adapter.abort_multipart_upload(ref, upload_id=upload_id)

    assert upload_id == "upload-123"
    assert part == UploadedPart(part_number=1, etag="etag-1")
    assert completed == CompletedMultipartUpload(etag="complete-etag", version_id="version-1")


@pytest.mark.parametrize(
    ("provider_code", "expected_exception"),
    [
        ("NoSuchKey", StorageObjectNotFoundError),
        ("AccessDenied", StorageAuthorizationError),
        ("Conflict", StorageConflictError),
        ("InvalidPart", StorageMultipartStateError),
        ("ServiceUnavailable", StorageTransientError),
        ("UnexpectedFailure", StorageProviderError),
    ],
)
def test_s3_storage_adapter_translates_provider_errors(
    provider_code: str,
    expected_exception: type[Exception],
) -> None:
    client = FakeS3Client()
    client.mode = provider_code
    adapter = S3StorageAdapter(client=client, bucket="cordis-artifacts")

    with pytest.raises(expected_exception):
        adapter.stat_object(_artifact_ref())
