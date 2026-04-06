from uuid import UUID

from pydantic import BaseModel


class TagResponse(BaseModel):
    id: UUID
    repository_id: int
    name: str
    version_id: UUID
    version_name: str


class TagListResponse(BaseModel):
    items: list[TagResponse]
