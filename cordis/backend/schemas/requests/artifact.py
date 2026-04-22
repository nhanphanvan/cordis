from uuid import UUID

from pydantic import BaseModel


class ArtifactCreateRequest(BaseModel):
    repository_id: int
    path: str
    checksum: str
    size: int


class VersionArtifactCreateRequest(BaseModel):
    artifact_id: UUID


class VersionArtifactPathClearRequest(BaseModel):
    path: str


class ResourceCheckRequest(BaseModel):
    version_id: UUID
    path: str
    checksum: str
    size: int
