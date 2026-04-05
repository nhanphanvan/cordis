from pydantic import BaseModel


class UploadSessionPartResponse(BaseModel):
    part_number: int
    etag: str


class UploadSessionResponse(BaseModel):
    id: str
    repository_id: int
    version_id: str
    artifact_id: str | None
    path: str
    checksum: str
    size: int
    upload_id: str
    status: str
    error_message: str | None
    parts: list[UploadSessionPartResponse]
