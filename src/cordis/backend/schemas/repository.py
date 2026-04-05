from pydantic import BaseModel


class RepositoryCreateRequest(BaseModel):
    name: str
    description: str | None = None
    is_public: bool = False


class RepositoryUpdateRequest(BaseModel):
    description: str | None = None
    is_public: bool


class RepositoryResponse(BaseModel):
    id: int
    name: str
    description: str | None
    is_public: bool


class RepositoryListResponse(BaseModel):
    items: list[RepositoryResponse]


class RepositoryAccessResponse(BaseModel):
    repository_id: int
    access: str


class RepositoryMemberMutationRequest(BaseModel):
    user_id: int
    role: str


class RepositoryMemberRoleUpdateRequest(BaseModel):
    role: str


class RepositoryMemberItem(BaseModel):
    email: str
    role: str


class RepositoryMembersResponse(BaseModel):
    items: list[RepositoryMemberItem]
