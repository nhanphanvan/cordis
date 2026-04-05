from pydantic import BaseModel


class UserResponse(BaseModel):
    id: int
    email: str
    is_active: bool
    is_admin: bool


class UserListResponse(BaseModel):
    items: list[UserResponse]


class UserUpdateRequest(BaseModel):
    email: str | None = None
    is_active: bool | None = None
    is_admin: bool | None = None


class UserCreateRequest(BaseModel):
    email: str
    password: str
    is_active: bool = True
    is_admin: bool = False


class UserRepositoryItem(BaseModel):
    repository_id: int
    repository_name: str
    role_name: str


class UserRepositoryListResponse(BaseModel):
    items: list[UserRepositoryItem]
