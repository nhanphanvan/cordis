from pydantic import BaseModel


class TagResponse(BaseModel):
    id: str
    repository_id: int
    name: str
    version_id: str
    version_name: str


class TagListResponse(BaseModel):
    items: list[TagResponse]
