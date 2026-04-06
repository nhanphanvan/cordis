from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from cordis.backend.api.dependencies import (
    get_current_user,
    get_optional_current_user,
    get_uow,
)
from cordis.backend.exceptions import AppStatus
from cordis.backend.models import User
from cordis.backend.policies import RepositoryPolicy, authorize
from cordis.backend.repositories.unit_of_work import UnitOfWork
from cordis.backend.schemas.requests.repository import (
    RepositoryCreateRequest,
    RepositoryMemberMutationRequest,
    RepositoryMemberRoleUpdateRequest,
    RepositoryUpdateRequest,
)
from cordis.backend.schemas.responses.repository import (
    RepositoryAccessResponse,
    RepositoryListResponse,
    RepositoryMemberItem,
    RepositoryMembersResponse,
    RepositoryResponse,
)
from cordis.backend.schemas.responses.tag import TagListResponse, TagResponse
from cordis.backend.schemas.responses.version import VersionListResponse, VersionResponse
from cordis.backend.services.repository import RepositoryService
from cordis.backend.services.tag import TagService
from cordis.backend.services.version import VersionService
from cordis.backend.validators.repository import (
    ROLE_RANK,
    BearerUserRequiredValidator,
    RepositoryAccessValidator,
    RepositoryCreateValidator,
    RepositoryMemberCreateValidator,
    RepositoryMemberDeleteValidator,
    RepositoryMemberRoleUpdateValidator,
)

router = APIRouter(prefix="/repositories", tags=["repositories"])


def _member_item_from_membership(email: str, role: str) -> RepositoryMemberItem:
    return RepositoryMemberItem(email=email, role=role)


def _repository_response(repository_id: int, name: str, description: str | None, is_public: bool) -> RepositoryResponse:
    return RepositoryResponse(id=repository_id, name=name, description=description, is_public=is_public)


def _version_response(version_id: UUID, repository_id: int, name: str, description: str | None) -> VersionResponse:
    return VersionResponse(id=version_id, repository_id=repository_id, name=name, description=description)


def _tag_response(tag_id: UUID, repository_id: int, name: str, version_id: UUID, version_name: str) -> TagResponse:
    return TagResponse(
        id=tag_id,
        repository_id=repository_id,
        name=name,
        version_id=version_id,
        version_name=version_name,
    )


@router.post("", response_model=RepositoryResponse, status_code=201)
async def create_repository(
    request: RepositoryCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> RepositoryResponse:
    await authorize(
        current_user,
        RepositoryPolicy.create,
        message="Admin privileges required",
        app_status=AppStatus.ERROR_ADMIN_PRIVILEGES_REQUIRED,
    )
    owner_role = await RepositoryCreateValidator.validate(uow=uow, request=request)
    repository = await RepositoryService(uow).create_repository(
        name=request.name,
        description=request.description,
        is_public=request.is_public,
        creator=current_user,
        owner_role=owner_role,
    )
    return _repository_response(repository.id, repository.name, repository.description, repository.is_public)


@router.get("", response_model=RepositoryListResponse)
async def list_repositories(
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> RepositoryListResponse:
    await authorize(
        current_user,
        RepositoryPolicy.list,
        message="Admin privileges required",
        app_status=AppStatus.ERROR_ADMIN_PRIVILEGES_REQUIRED,
    )
    repositories = await RepositoryService(uow).list_repositories()
    return RepositoryListResponse(
        items=[_repository_response(item.id, item.name, item.description, item.is_public) for item in repositories]
    )


@router.get("/{repository_id}", response_model=RepositoryResponse)
async def get_repository(
    repository_id: int,
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> RepositoryResponse:
    access = await RepositoryAccessValidator.validate(uow=uow, repository_id=repository_id, current_user=current_user)
    await authorize(
        current_user,
        RepositoryPolicy.viewer,
        access,
        unauthorized_message="Missing bearer token",
        unauthorized_app_status=AppStatus.ERROR_MISSING_BEARER_TOKEN,
    )
    repository = access.repository
    return _repository_response(repository.id, repository.name, repository.description, repository.is_public)


@router.patch("/{repository_id}", response_model=RepositoryResponse)
async def update_repository(
    request: RepositoryUpdateRequest,
    repository_id: int,
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> RepositoryResponse:
    current_user = await BearerUserRequiredValidator.validate(current_user=current_user)
    access = await RepositoryAccessValidator.validate(uow=uow, repository_id=repository_id, current_user=current_user)
    await authorize(current_user, RepositoryPolicy.owner, access)
    repository = await RepositoryService(uow).update_repository(
        repository=access.repository,
        description=request.description,
        is_public=request.is_public,
    )
    return _repository_response(repository.id, repository.name, repository.description, repository.is_public)


@router.delete("/{repository_id}", response_model=RepositoryResponse)
async def delete_repository(
    repository_id: int,
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> RepositoryResponse:
    current_user = await BearerUserRequiredValidator.validate(current_user=current_user)
    access = await RepositoryAccessValidator.validate(uow=uow, repository_id=repository_id, current_user=current_user)
    await authorize(current_user, RepositoryPolicy.owner, access)
    repository = await RepositoryService(uow).delete_repository(access.repository)
    return _repository_response(repository.id, repository.name, repository.description, repository.is_public)


@router.get("/{repository_id}/auth-check/viewer", response_model=RepositoryAccessResponse)
async def check_viewer_access(
    repository_id: int,
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> RepositoryAccessResponse:
    access = await RepositoryAccessValidator.validate(uow=uow, repository_id=repository_id, current_user=current_user)
    await authorize(
        current_user,
        RepositoryPolicy.viewer,
        access,
        unauthorized_message="Missing bearer token",
        unauthorized_app_status=AppStatus.ERROR_MISSING_BEARER_TOKEN,
    )
    return RepositoryAccessResponse(repository_id=access.repository.id, access="viewer")


@router.get("/{repository_id}/auth-check/developer", response_model=RepositoryAccessResponse)
async def check_developer_access(
    repository_id: int,
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> RepositoryAccessResponse:
    current_user = await BearerUserRequiredValidator.validate(current_user=current_user)
    access = await RepositoryAccessValidator.validate(uow=uow, repository_id=repository_id, current_user=current_user)
    await authorize(current_user, RepositoryPolicy.developer, access)
    return RepositoryAccessResponse(repository_id=access.repository.id, access="developer")


@router.get("/{repository_id}/members", response_model=RepositoryMembersResponse)
async def list_members(
    repository_id: int,
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> RepositoryMembersResponse:
    current_user = await BearerUserRequiredValidator.validate(current_user=current_user)
    access = await RepositoryAccessValidator.validate(uow=uow, repository_id=repository_id, current_user=current_user)
    await authorize(current_user, RepositoryPolicy.owner, access)
    memberships = await uow.repository_members.list_for_repository(access.repository.id)
    memberships.sort(key=lambda item: (-ROLE_RANK[item.role.name], item.user.email))
    return RepositoryMembersResponse(
        items=[RepositoryMemberItem(email=item.user.email, role=item.role.name) for item in memberships]
    )


@router.get("/{repository_id}/versions", response_model=VersionListResponse)
async def list_versions(
    repository_id: int,
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> VersionListResponse:
    access = await RepositoryAccessValidator.validate(uow=uow, repository_id=repository_id, current_user=current_user)
    await authorize(
        current_user,
        RepositoryPolicy.viewer,
        access,
        unauthorized_message="Missing bearer token",
        unauthorized_app_status=AppStatus.ERROR_MISSING_BEARER_TOKEN,
    )
    versions = await VersionService(uow).list_for_repository(access.repository)
    return VersionListResponse(
        items=[_version_response(item.id, item.repository_id, item.name, item.description) for item in versions]
    )


@router.get("/{repository_id}/tags", response_model=TagListResponse)
async def list_tags(
    repository_id: int,
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> TagListResponse:
    access = await RepositoryAccessValidator.validate(uow=uow, repository_id=repository_id, current_user=current_user)
    await authorize(
        current_user,
        RepositoryPolicy.viewer,
        access,
        unauthorized_message="Missing bearer token",
        unauthorized_app_status=AppStatus.ERROR_MISSING_BEARER_TOKEN,
    )
    tags = await TagService(uow).list_for_repository(access.repository.id)
    return TagListResponse(
        items=[
            _tag_response(item.id, item.repository_id, item.name, item.version_id, item.version.name) for item in tags
        ]
    )


@router.post("/{repository_id}/members", response_model=RepositoryMemberItem, status_code=201)
async def add_member(
    request: RepositoryMemberMutationRequest,
    repository_id: int,
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> RepositoryMemberItem:
    current_user = await BearerUserRequiredValidator.validate(current_user=current_user)
    access = await RepositoryAccessValidator.validate(uow=uow, repository_id=repository_id, current_user=current_user)
    await authorize(current_user, RepositoryPolicy.owner, access)
    user, role = await RepositoryMemberCreateValidator.validate(
        uow=uow,
        repository_id=access.repository.id,
        request=request,
    )
    membership = await RepositoryService(uow).add_member(
        repository_id=access.repository.id,
        user=user,
        role=role,
    )
    return _member_item_from_membership(membership.user.email, membership.role.name)


@router.patch("/{repository_id}/members/{user_id}", response_model=RepositoryMemberItem)
async def update_member(
    user_id: int,
    request: RepositoryMemberRoleUpdateRequest,
    repository_id: int,
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> RepositoryMemberItem:
    current_user = await BearerUserRequiredValidator.validate(current_user=current_user)
    access = await RepositoryAccessValidator.validate(uow=uow, repository_id=repository_id, current_user=current_user)
    await authorize(current_user, RepositoryPolicy.owner, access)
    membership, role = await RepositoryMemberRoleUpdateValidator.validate(
        uow=uow,
        repository_id=access.repository.id,
        user_id=user_id,
        request=request,
    )
    membership = await RepositoryService(uow).update_member_role(membership=membership, role=role)
    return _member_item_from_membership(membership.user.email, membership.role.name)


@router.delete("/{repository_id}/members/{user_id}", response_model=RepositoryMemberItem)
async def remove_member(
    user_id: int,
    repository_id: int,
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> RepositoryMemberItem:
    current_user = await BearerUserRequiredValidator.validate(current_user=current_user)
    access = await RepositoryAccessValidator.validate(uow=uow, repository_id=repository_id, current_user=current_user)
    await authorize(current_user, RepositoryPolicy.owner, access)
    membership = await RepositoryMemberDeleteValidator.validate(
        uow=uow,
        repository_id=access.repository.id,
        user_id=user_id,
    )
    membership = await RepositoryService(uow).remove_member(membership)
    return _member_item_from_membership(membership.user.email, membership.role.name)
