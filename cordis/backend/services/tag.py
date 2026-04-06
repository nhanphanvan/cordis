from uuid import UUID

from cordis.backend.models import VersionTag
from cordis.backend.models.version import Version
from cordis.backend.repositories.unit_of_work import UnitOfWork


class TagService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def create_tag(self, *, version: Version, name: str) -> VersionTag:
        tag = await self.uow.version_tags.create(repository_id=version.repository_id, version_id=version.id, name=name)
        await self.uow.commit()
        refreshed = await self.uow.version_tags.get_with_version(tag.id)
        return refreshed or tag

    async def get_tag(self, tag_id: UUID) -> VersionTag | None:
        return await self.uow.version_tags.get_with_version(tag_id)

    async def get_by_repository_and_name(self, *, repository_id: int, name: str) -> VersionTag | None:
        return await self.uow.version_tags.get_by_repository_and_name(repository_id=repository_id, name=name)

    async def list_for_repository(self, repository_id: int) -> list[VersionTag]:
        return await self.uow.version_tags.list_for_repository(repository_id)

    async def delete_tag(self, tag: VersionTag) -> VersionTag:
        await self.uow.version_tags.delete(tag)
        await self.uow.commit()
        return tag
