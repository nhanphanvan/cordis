from pydantic import BaseModel


class ArtifactCreateRequest(BaseModel):
    repository_id: int
    path: str
    checksum: str
    size: int


class ArtifactResponse(BaseModel):
    id: str
    repository_id: int
    path: str
    name: str
    checksum: str
    size: int


class ArtifactListResponse(BaseModel):
    items: list[ArtifactResponse]


class VersionArtifactCreateRequest(BaseModel):
    artifact_id: str


class ResourceCheckRequest(BaseModel):
    version_id: str
    path: str
    checksum: str
    size: int


class ResourceCheckResponse(BaseModel):
    status: str
    artifact_id: str | None


class ArtifactDownloadResponse(BaseModel):
    artifact_id: str
    download_url: str
    expires_in: int
