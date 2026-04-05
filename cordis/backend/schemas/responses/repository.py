from pydantic import BaseModel


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


class RepositoryMemberItem(BaseModel):
    email: str
    role: str


class RepositoryMembersResponse(BaseModel):
    items: list[RepositoryMemberItem]
