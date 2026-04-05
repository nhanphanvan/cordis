from typing import Annotated

from fastapi import APIRouter, Depends

from cordis.backend.api.dependencies import (
    get_admin_user,
    get_uow,
    require_repository_developer,
    require_repository_owner_or_admin,
    require_repository_viewer,
)
from cordis.backend.models import User
from cordis.backend.repositories.unit_of_work import UnitOfWork
from cordis.backend.schemas.repository import (
    RepositoryAccessResponse,
    RepositoryCreateRequest,
    RepositoryListResponse,
    RepositoryMemberItem,
    RepositoryMemberMutationRequest,
    RepositoryMemberRoleUpdateRequest,
    RepositoryMembersResponse,
    RepositoryResponse,
    RepositoryUpdateRequest,
)
from cordis.backend.schemas.tag import TagListResponse, TagResponse
from cordis.backend.schemas.version import VersionListResponse, VersionResponse
from cordis.backend.services.authorization import ROLE_RANK, RepositoryAccessContext
from cordis.backend.services.repository import RepositoryService
from cordis.backend.services.tag import TagService
from cordis.backend.services.version import VersionService

router = APIRouter(prefix="/repositories", tags=["repositories"])


def _member_item_from_membership(email: str, role: str) -> RepositoryMemberItem:
    return RepositoryMemberItem(email=email, role=role)


def _repository_response(repository_id: int, name: str, description: str | None, is_public: bool) -> RepositoryResponse:
    return RepositoryResponse(id=repository_id, name=name, description=description, is_public=is_public)


def _version_response(version_id: str, repository_id: int, name: str) -> VersionResponse:
    return VersionResponse(id=version_id, repository_id=repository_id, name=name)


def _tag_response(tag_id: str, repository_id: int, name: str, version_id: str, version_name: str) -> TagResponse:
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
    current_user: Annotated[User, Depends(get_admin_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> RepositoryResponse:
    repository = await RepositoryService(uow).create_repository(
        name=request.name,
        description=request.description,
        is_public=request.is_public,
        creator=current_user,
    )
    return _repository_response(repository.id, repository.name, repository.description, repository.is_public)


@router.get("", response_model=RepositoryListResponse)
async def list_repositories(
    _current_user: Annotated[User, Depends(get_admin_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> RepositoryListResponse:
    repositories = await RepositoryService(uow).list_repositories()
    return RepositoryListResponse(
        items=[_repository_response(item.id, item.name, item.description, item.is_public) for item in repositories]
    )


@router.get("/{repository_id}", response_model=RepositoryResponse)
async def get_repository(
    access: Annotated[RepositoryAccessContext, Depends(require_repository_viewer)],
) -> RepositoryResponse:
    repository = access.repository
    return _repository_response(repository.id, repository.name, repository.description, repository.is_public)


@router.patch("/{repository_id}", response_model=RepositoryResponse)
async def update_repository(
    request: RepositoryUpdateRequest,
    access: Annotated[RepositoryAccessContext, Depends(require_repository_owner_or_admin)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> RepositoryResponse:
    repository = await RepositoryService(uow).update_repository(
        repository_id=access.repository.id,
        description=request.description,
        is_public=request.is_public,
    )
    return _repository_response(repository.id, repository.name, repository.description, repository.is_public)


@router.delete("/{repository_id}", response_model=RepositoryResponse)
async def delete_repository(
    access: Annotated[RepositoryAccessContext, Depends(require_repository_owner_or_admin)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> RepositoryResponse:
    repository = await RepositoryService(uow).delete_repository(access.repository.id)
    return _repository_response(repository.id, repository.name, repository.description, repository.is_public)


@router.get("/{repository_id}/auth-check/viewer", response_model=RepositoryAccessResponse)
async def check_viewer_access(
    access: Annotated[RepositoryAccessContext, Depends(require_repository_viewer)],
) -> RepositoryAccessResponse:
    return RepositoryAccessResponse(repository_id=access.repository.id, access="viewer")


@router.get("/{repository_id}/auth-check/developer", response_model=RepositoryAccessResponse)
async def check_developer_access(
    access: Annotated[RepositoryAccessContext, Depends(require_repository_developer)],
) -> RepositoryAccessResponse:
    return RepositoryAccessResponse(repository_id=access.repository.id, access="developer")


@router.get("/{repository_id}/members", response_model=RepositoryMembersResponse)
async def list_members(
    access: Annotated[RepositoryAccessContext, Depends(require_repository_owner_or_admin)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> RepositoryMembersResponse:
    memberships = await uow.repository_members.list_for_repository(access.repository.id)
    memberships.sort(key=lambda item: (-ROLE_RANK[item.role.name], item.user.email))
    return RepositoryMembersResponse(
        items=[RepositoryMemberItem(email=item.user.email, role=item.role.name) for item in memberships]
    )


@router.get("/{repository_id}/versions", response_model=VersionListResponse)
async def list_versions(
    access: Annotated[RepositoryAccessContext, Depends(require_repository_viewer)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> VersionListResponse:
    versions = await VersionService(uow).list_for_repository(access.repository.id)
    return VersionListResponse(items=[_version_response(item.id, item.repository_id, item.name) for item in versions])


@router.get("/{repository_id}/tags", response_model=TagListResponse)
async def list_tags(
    access: Annotated[RepositoryAccessContext, Depends(require_repository_viewer)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> TagListResponse:
    tags = await TagService(uow).list_for_repository(access.repository.id)
    return TagListResponse(
        items=[
            _tag_response(item.id, item.repository_id, item.name, item.version_id, item.version.name) for item in tags
        ]
    )


@router.post("/{repository_id}/members", response_model=RepositoryMemberItem, status_code=201)
async def add_member(
    request: RepositoryMemberMutationRequest,
    access: Annotated[RepositoryAccessContext, Depends(require_repository_owner_or_admin)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> RepositoryMemberItem:
    membership = await RepositoryService(uow).add_member(
        repository_id=access.repository.id,
        user_id=request.user_id,
        role_name=request.role,
    )
    return _member_item_from_membership(membership.user.email, membership.role.name)


@router.patch("/{repository_id}/members/{user_id}", response_model=RepositoryMemberItem)
async def update_member(
    user_id: int,
    request: RepositoryMemberRoleUpdateRequest,
    access: Annotated[RepositoryAccessContext, Depends(require_repository_owner_or_admin)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> RepositoryMemberItem:
    membership = await RepositoryService(uow).update_member_role(
        repository_id=access.repository.id,
        user_id=user_id,
        role_name=request.role,
    )
    return _member_item_from_membership(membership.user.email, membership.role.name)


@router.delete("/{repository_id}/members/{user_id}", response_model=RepositoryMemberItem)
async def remove_member(
    user_id: int,
    access: Annotated[RepositoryAccessContext, Depends(require_repository_owner_or_admin)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> RepositoryMemberItem:
    membership = await RepositoryService(uow).remove_member(
        repository_id=access.repository.id,
        user_id=user_id,
    )
    return _member_item_from_membership(membership.user.email, membership.role.name)
