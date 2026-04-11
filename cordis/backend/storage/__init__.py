"""Backend storage package for object-store adapters and transfer helpers."""

from cordis.backend.storage.aws import AwsS3StorageClient
from cordis.backend.storage.errors import (
    StorageAuthorizationError,
    StorageConflictError,
    StorageMultipartStateError,
    StorageObjectNotFoundError,
    StorageProviderError,
    StorageTransientError,
)
from cordis.backend.storage.minio import MinioStorageClient
from cordis.backend.storage.protocol import StorageAdapter
from cordis.backend.storage.s3 import S3ClientProtocol, S3StorageAdapter
from cordis.backend.storage.types import (
    CompletedMultipartUpload,
    ObjectMetadata,
    StorageObjectRef,
    UploadedPart,
)

__all__ = [
    "AwsS3StorageClient",
    "CompletedMultipartUpload",
    "MinioStorageClient",
    "ObjectMetadata",
    "S3ClientProtocol",
    "S3StorageAdapter",
    "StorageAdapter",
    "StorageAuthorizationError",
    "StorageConflictError",
    "StorageMultipartStateError",
    "StorageObjectNotFoundError",
    "StorageObjectRef",
    "StorageProviderError",
    "StorageTransientError",
    "UploadedPart",
]
