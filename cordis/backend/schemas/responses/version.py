from pydantic import BaseModel


class VersionResponse(BaseModel):
    id: str
    repository_id: int
    name: str


class VersionListResponse(BaseModel):
    items: list[VersionResponse]
