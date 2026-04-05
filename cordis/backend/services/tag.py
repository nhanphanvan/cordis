from cordis.backend.exceptions import AppStatus, NotFoundError, NotUniqueError, UnprocessableEntityError
from cordis.backend.models import VersionTag
from cordis.backend.repositories.unit_of_work import UnitOfWork


class TagService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def create_tag(self, *, repository_id: int, version_id: str, name: str) -> VersionTag:
        existing = await self.uow.version_tags.get_by_repository_and_name(repository_id=repository_id, name=name)
        if existing is not None:
            raise NotUniqueError(
                "Tag name already exists in repository",
                app_status=AppStatus.ERROR_TAG_NAME_ALREADY_EXISTS,
            )

        repository = await self.uow.repositories.get(repository_id)
        if repository is None:
            raise NotFoundError("Repository not found", app_status=AppStatus.ERROR_REPOSITORY_NOT_FOUND)
        version = await self.uow.versions.get(version_id)
        if version is None:
            raise NotFoundError("Version not found", app_status=AppStatus.ERROR_VERSION_NOT_FOUND)
        if version.repository_id != repository_id:
            raise UnprocessableEntityError(
                "Version does not belong to repository",
                app_status=AppStatus.ERROR_TAG_VERSION_REPOSITORY_MISMATCH,
            )

        tag = await self.uow.version_tags.create(repository_id=repository_id, version_id=version_id, name=name)
        await self.uow.commit()
        refreshed = await self.uow.version_tags.get_with_version(tag.id)
        return refreshed or tag

    async def get_tag(self, tag_id: str) -> VersionTag:
        tag = await self.uow.version_tags.get_with_version(tag_id)
        if tag is None:
            raise NotFoundError("Tag not found", app_status=AppStatus.ERROR_TAG_NOT_FOUND)
        return tag

    async def get_by_repository_and_name(self, *, repository_id: int, name: str) -> VersionTag:
        tag = await self.uow.version_tags.get_by_repository_and_name(repository_id=repository_id, name=name)
        if tag is None:
            raise NotFoundError("Tag not found", app_status=AppStatus.ERROR_TAG_NOT_FOUND)
        return tag

    async def list_for_repository(self, repository_id: int) -> list[VersionTag]:
        repository = await self.uow.repositories.get(repository_id)
        if repository is None:
            raise NotFoundError("Repository not found", app_status=AppStatus.ERROR_REPOSITORY_NOT_FOUND)
        return await self.uow.version_tags.list_for_repository(repository_id)

    async def delete_tag(self, tag_id: str) -> VersionTag:
        tag = await self.get_tag(tag_id)
        await self.uow.version_tags.delete(tag)
        await self.uow.commit()
        return tag
