import json
from typing import Any

import pytest
from minio.error import S3Error

from cordis.backend.config import build_config
from cordis.backend.exceptions import AppStatus, InternalServerError
from cordis.backend.storage import (
    AwsS3StorageClient,
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


class FakeBotoClientError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.response = {"Error": {"Code": code}}


class FakeS3Client:
    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []
        self.mode = "ok"
        self.public_prefixes: set[str] = set()

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

    def create_public_object_url(self, *, bucket: str, key: str, version_id: str) -> str:
        self.calls.append(("create_public_object_url", bucket, key, version_id))
        if self.mode != "ok":
            raise FakeProviderError(self.mode)
        return f"https://example.invalid/{bucket}/{key}?versionId={version_id}"

    def ensure_public_prefix_access(self, *, bucket: str, prefix: str) -> bool:
        self.calls.append(("ensure_public_prefix_access", bucket, prefix))
        if self.mode != "ok":
            raise FakeProviderError(self.mode)
        created = prefix not in self.public_prefixes
        self.public_prefixes.add(prefix)
        return created

    def disable_public_prefix_access(self, *, bucket: str, prefix: str) -> bool:
        self.calls.append(("disable_public_prefix_access", bucket, prefix))
        if self.mode != "ok":
            raise FakeProviderError(self.mode)
        existed = prefix in self.public_prefixes
        self.public_prefixes.discard(prefix)
        return existed

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
        self.get_bucket_policy_mode = "ok"
        self.bucket_exists_result = True
        self.versioning_status = "Enabled"
        self.policy_json = ""
        self._base_url = type(
            "BaseUrl",
            (),
            {"is_https": bool(kwargs.get("secure", True)), "host": args[0] if args else "localhost:9000"},
        )()

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

    def get_bucket_policy(self, bucket_name: str) -> str:
        self.calls.append(("get_bucket_policy", bucket_name))
        if self.get_bucket_policy_mode == "NoSuchBucketPolicy":
            raise S3Error(
                code="NoSuchBucketPolicy",
                message="The bucket policy does not exist",
                resource=f"/{bucket_name}",
                request_id="test-request-id",
                host_id="test-host-id",
                response=None,
                bucket_name=bucket_name,
                object_name=None,
            )
        if self.mode != "ok":
            raise FakeProviderError(self.mode)
        return self.policy_json

    def set_bucket_policy(self, bucket_name: str, policy: str) -> None:
        self.calls.append(("set_bucket_policy", bucket_name, policy))
        if self.mode != "ok":
            raise FakeProviderError(self.mode)
        self.policy_json = policy

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


class FakeAwsSdk:
    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []
        self.mode = "ok"
        self.versioning_status = "Enabled"
        self.policy_json: str | None = None
        self.public_access_block = {
            "BlockPublicPolicy": False,
            "RestrictPublicBuckets": False,
        }
        self.meta = type(
            "Meta",
            (),
            {
                "endpoint_url": "https://s3.us-east-1.amazonaws.com",
                "config": type("Config", (), {"region_name": "us-east-1"})(),
            },
        )()

    def head_bucket(self, *, Bucket: str) -> None:
        self.calls.append(("head_bucket", Bucket))
        if self.mode == "NoSuchBucket":
            raise FakeBotoClientError("NoSuchBucket")
        if self.mode == "AccessDenied":
            raise FakeBotoClientError("AccessDenied")

    def get_bucket_versioning(self, *, Bucket: str) -> dict[str, Any]:
        self.calls.append(("get_bucket_versioning", Bucket))
        if self.mode == "AccessDenied":
            raise FakeBotoClientError("AccessDenied")
        return {"Status": self.versioning_status} if self.versioning_status is not None else {}

    def head_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        self.calls.append(("head_object", Bucket, Key))
        if self.mode != "ok":
            raise FakeBotoClientError(self.mode)
        return {"ETag": '"sha256:abc123"', "ContentLength": 1024}

    def put_object(self, *, Bucket: str, Key: str, Body: bytes, ChecksumSHA256: str | None = None) -> dict[str, Any]:
        self.calls.append(("put_object", Bucket, Key, Body, ChecksumSHA256))
        if self.mode != "ok":
            raise FakeBotoClientError(self.mode)
        return {"ETag": '"sha256:abc123"', "VersionId": "version-put-1"}

    def delete_object(self, *, Bucket: str, Key: str) -> None:
        self.calls.append(("delete_object", Bucket, Key))
        if self.mode != "ok":
            raise FakeBotoClientError(self.mode)

    def generate_presigned_url(self, ClientMethod: str, Params: dict[str, Any], ExpiresIn: int) -> str:
        self.calls.append(("generate_presigned_url", ClientMethod, Params, ExpiresIn))
        if self.mode != "ok":
            raise FakeBotoClientError(self.mode)
        return f"https://example.invalid/{Params['Bucket']}/{Params['Key']}?expires={ExpiresIn}"

    def get_bucket_policy(self, *, Bucket: str) -> dict[str, Any]:
        self.calls.append(("get_bucket_policy", Bucket))
        if self.mode == "NoSuchBucketPolicy":
            raise FakeBotoClientError("NoSuchBucketPolicy")
        if self.mode != "ok":
            raise FakeBotoClientError(self.mode)
        if self.policy_json is None:
            raise FakeBotoClientError("NoSuchBucketPolicy")
        return {"Policy": self.policy_json}

    def put_bucket_policy(self, *, Bucket: str, Policy: str) -> None:
        self.calls.append(("put_bucket_policy", Bucket, Policy))
        if self.mode != "ok":
            raise FakeBotoClientError(self.mode)
        self.policy_json = Policy

    def delete_bucket_policy(self, *, Bucket: str) -> None:
        self.calls.append(("delete_bucket_policy", Bucket))
        if self.mode != "ok":
            raise FakeBotoClientError(self.mode)
        self.policy_json = None

    def get_public_access_block(self, *, Bucket: str) -> dict[str, Any]:
        self.calls.append(("get_public_access_block", Bucket))
        if self.mode != "ok":
            raise FakeBotoClientError(self.mode)
        return {"PublicAccessBlockConfiguration": self.public_access_block}

    def create_multipart_upload(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        self.calls.append(("create_multipart_upload", Bucket, Key))
        if self.mode != "ok":
            raise FakeBotoClientError(self.mode)
        return {"UploadId": "upload-123"}

    def upload_part(
        self,
        *,
        Bucket: str,
        Key: str,
        UploadId: str,
        PartNumber: int,
        Body: bytes,
    ) -> dict[str, Any]:
        self.calls.append(("upload_part", Bucket, Key, UploadId, PartNumber, Body))
        if self.mode != "ok":
            raise FakeBotoClientError(self.mode)
        return {"ETag": f'"etag-{PartNumber}"'}

    def complete_multipart_upload(
        self,
        *,
        Bucket: str,
        Key: str,
        UploadId: str,
        MultipartUpload: dict[str, Any],
    ) -> dict[str, Any]:
        self.calls.append(("complete_multipart_upload", Bucket, Key, UploadId, MultipartUpload))
        if self.mode != "ok":
            raise FakeBotoClientError(self.mode)
        return {"ETag": '"complete-etag"', "VersionId": "version-1"}

    def abort_multipart_upload(self, *, Bucket: str, Key: str, UploadId: str) -> None:
        self.calls.append(("abort_multipart_upload", Bucket, Key, UploadId))
        if self.mode != "ok":
            raise FakeBotoClientError(self.mode)


def _artifact_ref() -> StorageObjectRef:
    return StorageObjectRef(repository_id=42, artifact_id="artifact-123", path="models/weights.bin")


def test_s3_storage_adapter_builds_object_keys_and_maps_object_operations() -> None:
    client = FakeS3Client()
    adapter = S3StorageAdapter(client=client, bucket="cordis-artifacts", prefix="tenant-a")
    ref = _artifact_ref()

    metadata = adapter.stat_object(ref)
    upload_etag = adapter.put_object(ref, body=b"payload", checksum="sha256:abc123")
    download_url = adapter.get_download_url(ref, expires_in=900)
    public_url = adapter.get_public_url(ref, storage_version_id="version-1")
    published = adapter.ensure_repository_public_access(repository_id=42)
    unpublished = adapter.disable_repository_public_access(repository_id=42)
    adapter.delete_object(ref)

    assert metadata == ObjectMetadata(etag="sha256:abc123", size=1024)
    assert upload_etag == "sha256:abc123"
    assert download_url == (
        "https://example.invalid/cordis-artifacts/"
        "tenant-a/repositories/42/artifacts/artifact-123/models/weights.bin?expires=900"
    )
    assert public_url == (
        "https://example.invalid/cordis-artifacts/"
        "tenant-a/repositories/42/artifacts/artifact-123/models/weights.bin?versionId=version-1"
    )
    assert published is True
    assert unpublished is True
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
            "create_public_object_url",
            "cordis-artifacts",
            "tenant-a/repositories/42/artifacts/artifact-123/models/weights.bin",
            "version-1",
        ),
        ("ensure_public_prefix_access", "cordis-artifacts", "tenant-a/repositories/42"),
        ("disable_public_prefix_access", "cordis-artifacts", "tenant-a/repositories/42"),
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
    assert completed == CompletedMultipartUpload(etag="complete-etag", checksum=None, version_id="version-1")


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
    assert (
        client.create_public_object_url(bucket="cordis-artifacts", key="path/file.bin", version_id="version-1")
        == "http://localhost:9000/cordis-artifacts/path/file.bin?versionId=version-1"
    )
    assert client.ensure_public_prefix_access(bucket="cordis-artifacts", prefix="tenant/repositories/42") is True
    assert client.disable_public_prefix_access(bucket="cordis-artifacts", prefix="tenant/repositories/42") is True
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


def test_minio_storage_client_uses_prefix_scoped_public_policy_statement() -> None:
    sdk = FakeMinioSdk("localhost:9000", access_key="minioadmin", secret_key="minioadmin", secure=False)
    client = MinioStorageClient(sdk)

    changed = client.ensure_public_prefix_access(bucket="cordis-artifacts", prefix="tenant/repositories/42")
    policy = json.loads(sdk.policy_json)

    assert changed is True
    assert policy == {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "CordisPublicPrefixtenant_repositories_42",
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:GetObject"],
                "Resource": ["arn:aws:s3:::cordis-artifacts/tenant/repositories/42/*"],
            }
        ],
    }


def test_minio_storage_client_initializes_public_policy_when_bucket_policy_is_missing() -> None:
    sdk = FakeMinioSdk("localhost:9000", access_key="minioadmin", secret_key="minioadmin", secure=False)
    sdk.get_bucket_policy_mode = "NoSuchBucketPolicy"
    client = MinioStorageClient(sdk)

    changed = client.ensure_public_prefix_access(bucket="cordis-artifacts", prefix="tenant/repositories/42")
    policy = json.loads(sdk.policy_json)

    assert changed is True
    assert policy == {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "CordisPublicPrefixtenant_repositories_42",
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:GetObject"],
                "Resource": ["arn:aws:s3:::cordis-artifacts/tenant/repositories/42/*"],
            }
        ],
    }


def test_minio_storage_client_disable_public_prefix_access_removes_only_cordis_statement() -> None:
    sdk = FakeMinioSdk("localhost:9000", access_key="minioadmin", secret_key="minioadmin", secure=False)
    sdk.policy_json = json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "KeepMe",
                    "Effect": "Allow",
                    "Principal": {"AWS": ["*"]},
                    "Action": ["s3:GetObject"],
                    "Resource": ["arn:aws:s3:::cordis-artifacts/shared/*"],
                },
                {
                    "Sid": "CordisPublicPrefixtenant_repositories_42",
                    "Effect": "Allow",
                    "Principal": {"AWS": ["*"]},
                    "Action": ["s3:GetObject"],
                    "Resource": ["arn:aws:s3:::cordis-artifacts/tenant/repositories/42/*"],
                },
            ],
        }
    )
    client = MinioStorageClient(sdk)

    changed = client.disable_public_prefix_access(bucket="cordis-artifacts", prefix="tenant/repositories/42")
    policy = json.loads(sdk.policy_json)

    assert changed is True
    assert policy == {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "KeepMe",
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:GetObject"],
                "Resource": ["arn:aws:s3:::cordis-artifacts/shared/*"],
            }
        ],
    }


def test_aws_s3_storage_client_maps_bucket_and_object_operations() -> None:
    sdk = FakeAwsSdk()
    client = AwsS3StorageClient(sdk)

    assert client.bucket_exists(bucket="cordis-artifacts") is True
    assert client.bucket_versioning_enabled(bucket="cordis-artifacts") is True
    assert client.head_object(bucket="cordis-artifacts", key="path/file.bin") == {
        "etag": "sha256:abc123",
        "content_length": 1024,
    }
    assert client.put_object(
        bucket="cordis-artifacts",
        key="path/file.bin",
        body=b"payload",
        checksum="sha256:abc123",
    ) == {
        "etag": "sha256:abc123",
        "version_id": "version-put-1",
    }
    assert (
        client.create_presigned_get_url(bucket="cordis-artifacts", key="path/file.bin", expires_in=900)
        == "https://example.invalid/cordis-artifacts/path/file.bin?expires=900"
    )
    assert (
        client.create_public_object_url(bucket="cordis-artifacts", key="path/file.bin", version_id="version-1")
        == "https://s3.us-east-1.amazonaws.com/cordis-artifacts/path/file.bin?versionId=version-1"
    )
    assert client.ensure_public_prefix_access(bucket="cordis-artifacts", prefix="tenant/repositories/42") is True
    assert client.disable_public_prefix_access(bucket="cordis-artifacts", prefix="tenant/repositories/42") is True
    assert client.create_multipart_upload(bucket="cordis-artifacts", key="path/file.bin") == {"upload_id": "upload-123"}
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


def test_aws_s3_storage_client_uses_prefix_scoped_public_policy_statement() -> None:
    sdk = FakeAwsSdk()
    client = AwsS3StorageClient(sdk)

    changed = client.ensure_public_prefix_access(bucket="cordis-artifacts", prefix="tenant/repositories/42")
    policy = json.loads(sdk.policy_json or "")

    assert changed is True
    assert policy == {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "CordisPublicPrefixtenant_repositories_42",
                "Effect": "Allow",
                "Principal": "*",
                "Action": ["s3:GetObject"],
                "Resource": ["arn:aws:s3:::cordis-artifacts/tenant/repositories/42/*"],
            }
        ],
    }


def test_aws_s3_storage_client_disable_public_prefix_access_removes_only_cordis_statement() -> None:
    sdk = FakeAwsSdk()
    sdk.policy_json = json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "KeepMe",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": ["s3:GetObject"],
                    "Resource": ["arn:aws:s3:::cordis-artifacts/shared/*"],
                },
                {
                    "Sid": "CordisPublicPrefixtenant_repositories_42",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": ["s3:GetObject"],
                    "Resource": ["arn:aws:s3:::cordis-artifacts/tenant/repositories/42/*"],
                },
            ],
        }
    )
    client = AwsS3StorageClient(sdk)

    changed = client.disable_public_prefix_access(bucket="cordis-artifacts", prefix="tenant/repositories/42")
    policy = json.loads(sdk.policy_json or "")

    assert changed is True
    assert policy == {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "KeepMe",
                "Effect": "Allow",
                "Principal": "*",
                "Action": ["s3:GetObject"],
                "Resource": ["arn:aws:s3:::cordis-artifacts/shared/*"],
            }
        ],
    }


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


def test_storage_factory_builds_aws_s3_adapter_for_real_s3(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_sdk = FakeAwsSdk()
    monkeypatch.setenv("CORDIS_STORAGE_PROVIDER", "s3")
    monkeypatch.setenv("CORDIS_STORAGE_BUCKET", "cordis-artifacts")
    monkeypatch.setenv("CORDIS_STORAGE_REGION", "us-east-1")
    monkeypatch.setattr("cordis.backend.storage.factory.boto3.client", lambda *args, **kwargs: fake_sdk)
    build_config.cache_clear()
    storage_factory.get_storage_adapter.cache_clear()

    adapter = storage_factory.get_storage_adapter()
    assert isinstance(adapter, S3StorageAdapter)
    assert isinstance(adapter.client, AwsS3StorageClient)
    assert fake_sdk.calls[:2] == [
        ("head_bucket", "cordis-artifacts"),
        ("get_bucket_versioning", "cordis-artifacts"),
    ]


def test_storage_factory_requires_minio_connection_settings(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CORDIS_STORAGE_PROVIDER", "minio")
    monkeypatch.delenv("CORDIS_STORAGE_ENDPOINT", raising=False)
    monkeypatch.delenv("CORDIS_STORAGE_ACCESS_KEY", raising=False)
    monkeypatch.delenv("CORDIS_STORAGE_SECRET_KEY", raising=False)
    build_config.cache_clear()
    storage_factory.get_storage_adapter.cache_clear()

    with pytest.raises(InternalServerError) as error_info:
        storage_factory.get_storage_adapter()

    assert error_info.value.app_status == AppStatus.ERROR_STORAGE_ADAPTER_NOT_CONFIGURED


def test_storage_factory_requires_existing_s3_bucket_and_enabled_versioning(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_sdk = FakeAwsSdk()
    fake_sdk.mode = "NoSuchBucket"
    monkeypatch.setenv("CORDIS_STORAGE_PROVIDER", "s3")
    monkeypatch.setenv("CORDIS_STORAGE_BUCKET", "cordis-artifacts")
    monkeypatch.setattr("cordis.backend.storage.factory.boto3.client", lambda *args, **kwargs: fake_sdk)
    build_config.cache_clear()
    storage_factory.get_storage_adapter.cache_clear()

    with pytest.raises(InternalServerError) as bucket_error:
        storage_factory.get_storage_adapter()

    assert bucket_error.value.app_status == AppStatus.ERROR_STORAGE_ADAPTER_NOT_CONFIGURED

    fake_sdk = FakeAwsSdk()
    fake_sdk.versioning_status = None
    monkeypatch.setattr("cordis.backend.storage.factory.boto3.client", lambda *args, **kwargs: fake_sdk)
    build_config.cache_clear()
    storage_factory.get_storage_adapter.cache_clear()

    with pytest.raises(InternalServerError) as versioning_error:
        storage_factory.get_storage_adapter()

    assert versioning_error.value.app_status == AppStatus.ERROR_STORAGE_ADAPTER_NOT_CONFIGURED


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
