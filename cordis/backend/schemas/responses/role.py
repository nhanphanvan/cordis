from pydantic import BaseModel


class RoleResponse(BaseModel):
    id: int
    name: str
    description: str | None


class RoleListResponse(BaseModel):
    items: list[RoleResponse]
