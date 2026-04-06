from uuid import UUID

from pydantic import BaseModel


class UploadSessionCreateRequest(BaseModel):
    version_id: UUID
    path: str
    checksum: str
    size: int


class UploadSessionPartCreateRequest(BaseModel):
    part_number: int
    content: str | None = None
    content_base64: str | None = None
