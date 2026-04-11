from uuid import UUID

from pydantic import BaseModel

from cordis.backend.enums import UploadSessionStatus


class UploadSessionPartResponse(BaseModel):
    part_number: int
    etag: str


class UploadSessionResponse(BaseModel):
    id: UUID
    repository_id: int
    version_id: UUID
    artifact_id: UUID | None
    path: str
    checksum: str
    size: int
    upload_id: str
    status: UploadSessionStatus
    error_message: str | None
    parts: list[UploadSessionPartResponse]
