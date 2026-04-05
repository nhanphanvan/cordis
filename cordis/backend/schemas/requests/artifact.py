from pydantic import BaseModel


class ArtifactCreateRequest(BaseModel):
    repository_id: int
    path: str
    checksum: str
    size: int


class VersionArtifactCreateRequest(BaseModel):
    artifact_id: str


class ResourceCheckRequest(BaseModel):
    version_id: str
    path: str
    checksum: str
    size: int
