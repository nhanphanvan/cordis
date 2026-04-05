from pydantic import BaseModel


class TagCreateRequest(BaseModel):
    repository_id: int
    version_id: str
    name: str
