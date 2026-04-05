from cordis.backend.models import Version
from cordis.backend.models.repository import Repository
from cordis.backend.repositories.unit_of_work import UnitOfWork


class VersionService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def create_version(self, *, repository: Repository, name: str) -> Version:
        version = await self.uow.versions.create(repository_id=repository.id, name=name)
        await self.uow.commit()
        return version

    async def get_version(self, version_id: str) -> Version | None:
        return await self.uow.versions.get(version_id)

    async def get_by_repository_and_name(self, *, repository_id: int, name: str) -> Version | None:
        return await self.uow.versions.get_by_repository_and_name(repository_id=repository_id, name=name)

    async def list_for_repository(self, repository: Repository) -> list[Version]:
        return await self.uow.versions.list_for_repository(repository.id)

    async def delete_version(self, version: Version) -> Version:
        await self.uow.versions.delete(version)
        await self.uow.commit()
        return version
