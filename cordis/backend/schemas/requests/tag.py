from uuid import UUID

from pydantic import BaseModel


class TagCreateRequest(BaseModel):
    repository_id: int
    version_id: UUID
    name: str
