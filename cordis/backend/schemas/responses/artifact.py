from pydantic import BaseModel


class ArtifactResponse(BaseModel):
    id: str
    repository_id: int
    path: str
    name: str
    checksum: str
    size: int


class ArtifactListResponse(BaseModel):
    items: list[ArtifactResponse]


class ResourceCheckResponse(BaseModel):
    status: str
    artifact_id: str | None


class ArtifactDownloadResponse(BaseModel):
    artifact_id: str
    download_url: str
    expires_in: int
