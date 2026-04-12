from pydantic import BaseModel

from cordis.backend.enums import RepositoryVisibility


class RepositoryCreateRequest(BaseModel):
    name: str
    description: str | None = None
    visibility: RepositoryVisibility = RepositoryVisibility.PRIVATE
    allow_public_object_urls: bool = False


class RepositoryUpdateRequest(BaseModel):
    description: str | None = None
    visibility: RepositoryVisibility
    allow_public_object_urls: bool


class RepositoryMemberMutationRequest(BaseModel):
    user_id: int
    role: str


class RepositoryMemberRoleUpdateRequest(BaseModel):
    role: str
