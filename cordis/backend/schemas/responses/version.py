from uuid import UUID

from pydantic import BaseModel


class VersionResponse(BaseModel):
    id: UUID
    repository_id: int
    name: str
    description: str | None


class VersionListResponse(BaseModel):
    items: list[VersionResponse]
