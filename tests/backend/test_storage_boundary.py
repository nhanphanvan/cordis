from typing import Any

import pytest

from cordis.backend.config import build_config
from cordis.backend.exceptions import AppStatus, InternalServerError
from cordis.backend.storage import (
    CompletedMultipartUpload,
    MinioStorageClient,
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
from cordis.backend.storage import (
    factory as storage_factory,
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


class FakeMinioSdk:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.args = args
        self.kwargs = kwargs
        self.calls: list[tuple[Any, ...]] = []
        self.mode = "ok"
        self.bucket_exists_result = True
        self.versioning_status = "Enabled"

    def bucket_exists(self, bucket_name: str) -> bool:
        self.calls.append(("bucket_exists", bucket_name))
        if self.mode != "ok":
            raise FakeProviderError(self.mode)
        return self.bucket_exists_result

    def make_bucket(self, bucket_name: str, location: str | None = None, object_lock: bool = False) -> None:
        self.calls.append(("make_bucket", bucket_name, location, object_lock))
        if self.mode != "ok":
            raise FakeProviderError(self.mode)

    def get_bucket_versioning(self, bucket_name: str) -> Any:
        self.calls.append(("get_bucket_versioning", bucket_name))
        if self.mode != "ok":
            raise FakeProviderError(self.mode)
        return type("Versioning", (), {"status": self.versioning_status})()

    def set_bucket_versioning(self, bucket_name: str, config: Any) -> None:
        self.calls.append(("set_bucket_versioning", bucket_name, getattr(config, "status", None)))
        if self.mode != "ok":
            raise FakeProviderError(self.mode)

    def stat_object(self, bucket_name: str, object_name: str) -> Any:
        self.calls.append(("stat_object", bucket_name, object_name))
        if self.mode != "ok":
            raise FakeProviderError(self.mode)
        return type("StatObject", (), {"etag": "sha256:abc123", "size": 1024})()

    def put_object(self, bucket_name: str, object_name: str, data: Any, length: int, content_type: str) -> Any:
        payload = data.read()
        self.calls.append(("put_object", bucket_name, object_name, payload, length, content_type))
        if self.mode != "ok":
            raise FakeProviderError(self.mode)
        return type("PutObjectResult", (), {"etag": "sha256:abc123", "version_id": "version-put-1"})()

    def remove_object(self, bucket_name: str, object_name: str) -> None:
        self.calls.append(("remove_object", bucket_name, object_name))
        if self.mode != "ok":
            raise FakeProviderError(self.mode)

    def presigned_get_object(
        self,
        bucket_name: str,
        object_name: str,
        *,
        expires: Any,
        version_id: str | None = None,
    ) -> str:
        self.calls.append(("presigned_get_object", bucket_name, object_name, int(expires.total_seconds()), version_id))
        if self.mode != "ok":
            raise FakeProviderError(self.mode)
        return f"https://example.invalid/{bucket_name}/{object_name}?expires={int(expires.total_seconds())}"

    def _create_multipart_upload(self, bucket_name: str, object_name: str, headers: dict[str, Any]) -> str:
        self.calls.append(("_create_multipart_upload", bucket_name, object_name, headers))
        if self.mode != "ok":
            raise FakeProviderError(self.mode)
        return "upload-123"

    def _upload_part(
        self,
        bucket_name: str,
        object_name: str,
        data: bytes,
        headers: dict[str, Any] | None,
        upload_id: str,
        part_number: int,
    ) -> str:
        self.calls.append(("_upload_part", bucket_name, object_name, data, headers, upload_id, part_number))
        if self.mode != "ok":
            raise FakeProviderError(self.mode)
        return f"etag-{part_number}"

    def _complete_multipart_upload(
        self,
        bucket_name: str,
        object_name: str,
        upload_id: str,
        parts: list[Any],
        ssec: Any = None,
    ) -> Any:
        self.calls.append(
            (
                "_complete_multipart_upload",
                bucket_name,
                object_name,
                upload_id,
                [(part.part_number, part.etag) for part in parts],
                ssec,
            )
        )
        if self.mode != "ok":
            raise FakeProviderError(self.mode)
        return type("CompleteResult", (), {"etag": "complete-etag", "version_id": "version-1"})()

    def _abort_multipart_upload(self, bucket_name: str, object_name: str, upload_id: str) -> None:
        self.calls.append(("_abort_multipart_upload", bucket_name, object_name, upload_id))
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


def test_minio_storage_client_maps_bucket_and_object_operations() -> None:
    sdk = FakeMinioSdk("localhost:9000", access_key="minioadmin", secret_key="minioadmin", secure=False)
    sdk.bucket_exists_result = False
    sdk.versioning_status = None
    client = MinioStorageClient(sdk)

    assert client.ensure_bucket_exists(bucket="cordis-artifacts", region="us-east-1") is True
    client.ensure_bucket_versioning_enabled(bucket="cordis-artifacts")
    assert client.head_object(bucket="cordis-artifacts", key="path/file.bin") == {
        "etag": "sha256:abc123",
        "content_length": 1024,
    }
    assert client.put_object(bucket="cordis-artifacts", key="path/file.bin", body=b"payload", checksum=None) == {
        "etag": "sha256:abc123",
        "version_id": "version-put-1",
    }
    assert (
        client.create_presigned_get_url(bucket="cordis-artifacts", key="path/file.bin", expires_in=900)
        == "https://example.invalid/cordis-artifacts/path/file.bin?expires=900"
    )
    upload_id = client.create_multipart_upload(bucket="cordis-artifacts", key="path/file.bin")
    assert upload_id == {"upload_id": "upload-123"}
    assert client.upload_part(
        bucket="cordis-artifacts",
        key="path/file.bin",
        upload_id="upload-123",
        part_number=1,
        body=b"chunk",
    ) == {"etag": "etag-1"}
    assert client.complete_multipart_upload(
        bucket="cordis-artifacts",
        key="path/file.bin",
        upload_id="upload-123",
        parts=[{"part_number": 1, "etag": "etag-1"}],
    ) == {"etag": "complete-etag", "version_id": "version-1"}
    client.abort_multipart_upload(bucket="cordis-artifacts", key="path/file.bin", upload_id="upload-123")
    client.delete_object(bucket="cordis-artifacts", key="path/file.bin")


def test_storage_factory_builds_minio_backed_adapter_and_bootstraps_bucket(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_sdk = FakeMinioSdk()
    fake_sdk.bucket_exists_result = False
    fake_sdk.versioning_status = None
    monkeypatch.setenv("CORDIS_STORAGE_PROVIDER", "minio")
    monkeypatch.setenv("CORDIS_STORAGE_ENDPOINT", "localhost:9000")
    monkeypatch.setenv("CORDIS_STORAGE_ACCESS_KEY", "minioadmin")
    monkeypatch.setenv("CORDIS_STORAGE_SECRET_KEY", "minioadmin")
    monkeypatch.setenv("CORDIS_STORAGE_BUCKET", "cordis-artifacts")
    monkeypatch.setenv("CORDIS_STORAGE_REGION", "us-east-1")
    monkeypatch.setenv("CORDIS_STORAGE_SECURE", "false")
    monkeypatch.setattr("cordis.backend.storage.factory.Minio", lambda *args, **kwargs: fake_sdk)
    build_config.cache_clear()
    storage_factory.get_storage_adapter.cache_clear()

    adapter = storage_factory.get_storage_adapter()
    assert isinstance(adapter, S3StorageAdapter)
    assert isinstance(adapter.client, MinioStorageClient)
    assert fake_sdk.calls[:3] == [
        ("bucket_exists", "cordis-artifacts"),
        ("make_bucket", "cordis-artifacts", "us-east-1", False),
        ("get_bucket_versioning", "cordis-artifacts"),
    ]
    assert fake_sdk.calls[3] == ("set_bucket_versioning", "cordis-artifacts", "Enabled")


def test_storage_factory_requires_minio_connection_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORDIS_STORAGE_PROVIDER", "minio")
    monkeypatch.delenv("CORDIS_STORAGE_ENDPOINT", raising=False)
    monkeypatch.delenv("CORDIS_STORAGE_ACCESS_KEY", raising=False)
    monkeypatch.delenv("CORDIS_STORAGE_SECRET_KEY", raising=False)
    build_config.cache_clear()
    storage_factory.get_storage_adapter.cache_clear()

    with pytest.raises(InternalServerError) as error_info:
        storage_factory.get_storage_adapter()

    assert error_info.value.app_status == AppStatus.ERROR_STORAGE_ADAPTER_NOT_CONFIGURED


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
