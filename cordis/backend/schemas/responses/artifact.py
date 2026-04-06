from uuid import UUID

from pydantic import BaseModel


class ArtifactResponse(BaseModel):
    id: UUID
    repository_id: int
    path: str
    name: str
    checksum: str
    size: int
    storage_version_id: str


class ArtifactListResponse(BaseModel):
    items: list[ArtifactResponse]


class ResourceCheckResponse(BaseModel):
    status: str
    artifact_id: UUID | None


class ArtifactDownloadResponse(BaseModel):
    artifact_id: UUID
    download_url: str
    expires_in: int
