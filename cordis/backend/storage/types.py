from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StorageObjectRef:
    repository_id: int
    artifact_id: str
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
    version_id: str | None
