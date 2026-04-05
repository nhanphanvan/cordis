from typing import Annotated

from fastapi import APIRouter, Depends, Query

from cordis.backend.api.dependencies import get_current_user, get_optional_current_user, get_uow
from cordis.backend.models import User
from cordis.backend.repositories.unit_of_work import UnitOfWork
from cordis.backend.schemas.requests.tag import TagCreateRequest
from cordis.backend.schemas.responses.tag import TagResponse
from cordis.backend.services.authorization import AuthorizationService
from cordis.backend.services.tag import TagService

router = APIRouter(prefix="/tags", tags=["tags"])


def _tag_response(tag_id: str, repository_id: int, name: str, version_id: str, version_name: str) -> TagResponse:
    return TagResponse(
        id=tag_id,
        repository_id=repository_id,
        name=name,
        version_id=version_id,
        version_name=version_name,
    )


@router.post("", response_model=TagResponse, status_code=201)
async def create_tag(
    request: TagCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> TagResponse:
    await AuthorizationService(uow).require_repository_access(
        repository_id=request.repository_id,
        required_role="developer",
        current_user=current_user,
    )
    tag = await TagService(uow).create_tag(
        repository_id=request.repository_id,
        version_id=request.version_id,
        name=request.name,
    )
    return _tag_response(tag.id, tag.repository_id, tag.name, tag.version_id, tag.version.name)


@router.get("/{tag_id}", response_model=TagResponse)
async def get_tag(
    tag_id: str,
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> TagResponse:
    tag = await TagService(uow).get_tag(tag_id)
    await AuthorizationService(uow).require_repository_access(
        repository_id=tag.repository_id,
        required_role="viewer",
        current_user=current_user,
    )
    return _tag_response(tag.id, tag.repository_id, tag.name, tag.version_id, tag.version.name)


@router.get("", response_model=TagResponse)
async def lookup_tag(
    repository_id: Annotated[int, Query()],
    name: Annotated[str, Query()],
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> TagResponse:
    await AuthorizationService(uow).require_repository_access(
        repository_id=repository_id,
        required_role="viewer",
        current_user=current_user,
    )
    tag = await TagService(uow).get_by_repository_and_name(repository_id=repository_id, name=name)
    return _tag_response(tag.id, tag.repository_id, tag.name, tag.version_id, tag.version.name)


@router.delete("/{tag_id}", response_model=TagResponse)
async def delete_tag(
    tag_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> TagResponse:
    tag = await TagService(uow).get_tag(tag_id)
    await AuthorizationService(uow).require_repository_access(
        repository_id=tag.repository_id,
        required_role="developer",
        current_user=current_user,
    )
    deleted = await TagService(uow).delete_tag(tag_id)
    return _tag_response(deleted.id, deleted.repository_id, deleted.name, deleted.version_id, deleted.version.name)
