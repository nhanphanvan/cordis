from pydantic import BaseModel


class UserResponse(BaseModel):
    id: int
    email: str
    is_active: bool
    is_admin: bool


class UserListResponse(BaseModel):
    items: list[UserResponse]


class UserRepositoryItem(BaseModel):
    repository_id: int
    repository_name: str
    role_name: str


class UserRepositoryListResponse(BaseModel):
    items: list[UserRepositoryItem]
