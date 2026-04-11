from pydantic import BaseModel

from cordis.backend.enums import RepositoryAccessRole


class RepositoryResponse(BaseModel):
    id: int
    name: str
    description: str | None
    is_public: bool


class RepositoryListResponse(BaseModel):
    items: list[RepositoryResponse]


class RepositoryAccessResponse(BaseModel):
    repository_id: int
    access: RepositoryAccessRole


class RepositoryMemberItem(BaseModel):
    email: str
    role: str


class RepositoryMembersResponse(BaseModel):
    items: list[RepositoryMemberItem]
