from uuid import UUID

from cordis.backend.exceptions import AppStatus, NotFoundError, NotUniqueError
from cordis.backend.models import Repository, Version
from cordis.backend.repositories.unit_of_work import UnitOfWork
from cordis.backend.schemas.requests.version import VersionCreateRequest

from .base import BaseValidator


class VersionCreateValidator(BaseValidator):
    @classmethod
    async def validate(cls, *, uow: UnitOfWork, request: VersionCreateRequest) -> Repository:
        existing = await uow.versions.get_by_repository_and_name(repository_id=request.repository_id, name=request.name)
        if existing is not None:
            raise NotUniqueError(
                "Version name already exists in repository",
                app_status=AppStatus.ERROR_VERSION_NAME_ALREADY_EXISTS,
            )
        repository = await uow.repositories.get(request.repository_id)
        if repository is None:
            raise NotFoundError("Repository not found", app_status=AppStatus.ERROR_REPOSITORY_NOT_FOUND)
        return repository


class VersionReadValidator(BaseValidator):
    @classmethod
    async def validate(cls, *, uow: UnitOfWork, version_id: UUID) -> Version:
        version = await uow.versions.get(version_id)
        if version is None:
            raise NotFoundError("Version not found", app_status=AppStatus.ERROR_VERSION_NOT_FOUND)
        return version


class VersionLookupValidator(BaseValidator):
    @classmethod
    async def validate(cls, *, uow: UnitOfWork, repository_id: int, name: str) -> Version:
        version = await uow.versions.get_by_repository_and_name(repository_id=repository_id, name=name)
        if version is None:
            raise NotFoundError("Version not found", app_status=AppStatus.ERROR_VERSION_NOT_FOUND)
        return version
