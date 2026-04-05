from cordis.backend.exceptions import AppStatus, NotFoundError, NotUniqueError
from cordis.backend.models import Version
from cordis.backend.repositories.unit_of_work import UnitOfWork


class VersionService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def create_version(self, *, repository_id: int, name: str) -> Version:
        existing = await self.uow.versions.get_by_repository_and_name(repository_id=repository_id, name=name)
        if existing is not None:
            raise NotUniqueError(
                "Version name already exists in repository",
                app_status=AppStatus.ERROR_VERSION_NAME_ALREADY_EXISTS,
            )

        repository = await self.uow.repositories.get(repository_id)
        if repository is None:
            raise NotFoundError("Repository not found", app_status=AppStatus.ERROR_REPOSITORY_NOT_FOUND)

        version = await self.uow.versions.create(repository_id=repository_id, name=name)
        await self.uow.commit()
        return version

    async def get_version(self, version_id: str) -> Version:
        version = await self.uow.versions.get(version_id)
        if version is None:
            raise NotFoundError("Version not found", app_status=AppStatus.ERROR_VERSION_NOT_FOUND)
        return version

    async def get_by_repository_and_name(self, *, repository_id: int, name: str) -> Version:
        version = await self.uow.versions.get_by_repository_and_name(repository_id=repository_id, name=name)
        if version is None:
            raise NotFoundError("Version not found", app_status=AppStatus.ERROR_VERSION_NOT_FOUND)
        return version

    async def list_for_repository(self, repository_id: int) -> list[Version]:
        repository = await self.uow.repositories.get(repository_id)
        if repository is None:
            raise NotFoundError("Repository not found", app_status=AppStatus.ERROR_REPOSITORY_NOT_FOUND)
        return await self.uow.versions.list_for_repository(repository_id)

    async def delete_version(self, version_id: str) -> Version:
        version = await self.get_version(version_id)
        await self.uow.versions.delete(version)
        await self.uow.commit()
        return version
