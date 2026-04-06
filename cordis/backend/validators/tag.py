from uuid import UUID

from cordis.backend.exceptions import AppStatus, NotFoundError, NotUniqueError, UnprocessableEntityError
from cordis.backend.models import Version, VersionTag
from cordis.backend.repositories.unit_of_work import UnitOfWork
from cordis.backend.schemas.requests.tag import TagCreateRequest

from .base import BaseValidator


class TagCreateValidator(BaseValidator):
    @classmethod
    async def validate(cls, *, uow: UnitOfWork, request: TagCreateRequest) -> Version:
        existing = await uow.version_tags.get_by_repository_and_name(
            repository_id=request.repository_id,
            name=request.name,
        )
        if existing is not None:
            raise NotUniqueError(
                "Tag name already exists in repository",
                app_status=AppStatus.ERROR_TAG_NAME_ALREADY_EXISTS,
            )
        version = await uow.versions.get(request.version_id)
        if version is None:
            raise NotFoundError("Version not found", app_status=AppStatus.ERROR_VERSION_NOT_FOUND)
        if version.repository_id != request.repository_id:
            raise UnprocessableEntityError(
                "Version does not belong to repository",
                app_status=AppStatus.ERROR_TAG_VERSION_REPOSITORY_MISMATCH,
            )
        return version


class TagReadValidator(BaseValidator):
    @classmethod
    async def validate(cls, *, uow: UnitOfWork, tag_id: UUID) -> VersionTag:
        tag = await uow.version_tags.get_with_version(tag_id)
        if tag is None:
            raise NotFoundError("Tag not found", app_status=AppStatus.ERROR_TAG_NOT_FOUND)
        return tag


class TagLookupValidator(BaseValidator):
    @classmethod
    async def validate(cls, *, uow: UnitOfWork, repository_id: int, name: str) -> VersionTag:
        tag = await uow.version_tags.get_by_repository_and_name(repository_id=repository_id, name=name)
        if tag is None:
            raise NotFoundError("Tag not found", app_status=AppStatus.ERROR_TAG_NOT_FOUND)
        return tag
