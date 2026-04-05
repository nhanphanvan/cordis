from typing import Annotated

from fastapi import APIRouter, Depends, Query

from cordis.backend.api.dependencies import get_current_user, get_optional_current_user, get_uow
from cordis.backend.exceptions import AppStatus
from cordis.backend.models import User
from cordis.backend.policies import TagPolicy, authorize
from cordis.backend.repositories.unit_of_work import UnitOfWork
from cordis.backend.schemas.requests.tag import TagCreateRequest
from cordis.backend.schemas.responses.tag import TagResponse
from cordis.backend.services.tag import TagService
from cordis.backend.validators.repository import RepositoryAccessValidator
from cordis.backend.validators.tag import TagCreateValidator, TagLookupValidator, TagReadValidator

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
    version = await TagCreateValidator.validate(uow=uow, request=request)
    access = await RepositoryAccessValidator.validate(
        uow=uow,
        repository_id=request.repository_id,
        current_user=current_user,
    )
    await authorize(current_user, TagPolicy.create, access)
    tag = await TagService(uow).create_tag(version=version, name=request.name)
    return _tag_response(tag.id, tag.repository_id, tag.name, tag.version_id, tag.version.name)


@router.get("/{tag_id}", response_model=TagResponse)
async def get_tag(
    tag_id: str,
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> TagResponse:
    tag = await TagReadValidator.validate(uow=uow, tag_id=tag_id)
    access = await RepositoryAccessValidator.validate(
        uow=uow,
        repository_id=tag.repository_id,
        current_user=current_user,
    )
    await authorize(
        current_user,
        TagPolicy.read,
        access,
        unauthorized_message="Missing bearer token",
        unauthorized_app_status=AppStatus.ERROR_MISSING_BEARER_TOKEN,
    )
    return _tag_response(tag.id, tag.repository_id, tag.name, tag.version_id, tag.version.name)


@router.get("", response_model=TagResponse)
async def lookup_tag(
    repository_id: Annotated[int, Query()],
    name: Annotated[str, Query()],
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> TagResponse:
    access = await RepositoryAccessValidator.validate(uow=uow, repository_id=repository_id, current_user=current_user)
    await authorize(
        current_user,
        TagPolicy.read,
        access,
        unauthorized_message="Missing bearer token",
        unauthorized_app_status=AppStatus.ERROR_MISSING_BEARER_TOKEN,
    )
    tag = await TagLookupValidator.validate(uow=uow, repository_id=repository_id, name=name)
    return _tag_response(tag.id, tag.repository_id, tag.name, tag.version_id, tag.version.name)


@router.delete("/{tag_id}", response_model=TagResponse)
async def delete_tag(
    tag_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> TagResponse:
    tag = await TagReadValidator.validate(uow=uow, tag_id=tag_id)
    access = await RepositoryAccessValidator.validate(
        uow=uow,
        repository_id=tag.repository_id,
        current_user=current_user,
    )
    await authorize(current_user, TagPolicy.delete, access)
    deleted = await TagService(uow).delete_tag(tag)
    return _tag_response(deleted.id, deleted.repository_id, deleted.name, deleted.version_id, deleted.version.name)
