from pydantic import BaseModel


class VersionCreateRequest(BaseModel):
    repository_id: int
    name: str


class VersionResponse(BaseModel):
    id: str
    repository_id: int
    name: str


class VersionListResponse(BaseModel):
    items: list[VersionResponse]
