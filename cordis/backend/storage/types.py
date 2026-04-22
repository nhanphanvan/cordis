from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class StorageObjectRef:
    repository_id: int
    artifact_id: UUID
    path: str


@dataclass(frozen=True, slots=True)
class ObjectMetadata:
    etag: str
    size: int


@dataclass(frozen=True, slots=True)
class UploadedPart:
    part_number: int
    etag: str


@dataclass(frozen=True, slots=True)
class CompletedMultipartUpload:
    etag: str
    checksum: str | None
