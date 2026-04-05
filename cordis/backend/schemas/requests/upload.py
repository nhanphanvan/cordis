from pydantic import BaseModel


class UploadSessionCreateRequest(BaseModel):
    version_id: str
    path: str
    checksum: str
    size: int


class UploadSessionPartCreateRequest(BaseModel):
    part_number: int
    content: str | None = None
    content_base64: str | None = None
