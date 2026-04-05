from pydantic import BaseModel


class RepositoryCreateRequest(BaseModel):
    name: str
    description: str | None = None
    is_public: bool = False


class RepositoryUpdateRequest(BaseModel):
    description: str | None = None
    is_public: bool


class RepositoryMemberMutationRequest(BaseModel):
    user_id: int
    role: str


class RepositoryMemberRoleUpdateRequest(BaseModel):
    role: str
