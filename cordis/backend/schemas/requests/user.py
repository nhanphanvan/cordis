from pydantic import BaseModel


class UserUpdateRequest(BaseModel):
    email: str | None = None
    is_active: bool | None = None
    is_admin: bool | None = None


class UserCreateRequest(BaseModel):
    email: str
    password: str
    is_active: bool = True
    is_admin: bool = False
