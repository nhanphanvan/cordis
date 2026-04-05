from pydantic import BaseModel


class RoleResponse(BaseModel):
    id: int
    name: str
    description: str | None


class RoleListResponse(BaseModel):
    items: list[RoleResponse]


class RoleCreateRequest(BaseModel):
    name: str
    description: str | None = None


class RoleUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
