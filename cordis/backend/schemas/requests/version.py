from pydantic import BaseModel


class VersionCreateRequest(BaseModel):
    repository_id: int
    name: str
    description: str | None = None
