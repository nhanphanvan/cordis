import logging

from cordis.backend.enums import RepositoryVisibility
from cordis.backend.exceptions import AppStatus, UnprocessableEntityError
from cordis.backend.models import Repository, RepositoryMember, User
from cordis.backend.models.role import Role
from cordis.backend.repositories.unit_of_work import UnitOfWork
from cordis.backend.storage import factory as storage_factory

logger = logging.getLogger(__name__)


class RepositoryService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def create_repository(
        self,
        *,
        name: str,
        description: str | None,
        visibility: RepositoryVisibility,
        allow_public_object_urls: bool,
        creator: User,
        owner_role: Role,
    ) -> Repository:
        repository = await self.uow.repositories.create(
            name=name,
            description=description,
            visibility=visibility.value,
            allow_public_object_urls=allow_public_object_urls,
        )
        if allow_public_object_urls:
            self._sync_public_object_access(repository_id=repository.id, allow_public_object_urls=True)
        await self.uow.repository_members.create(
            repository_id=repository.id,
            user_id=creator.id,
            role_id=owner_role.id,
        )
        await self.uow.commit()
        await self.uow.refresh(repository)
        logger.info(
            "Repository created repository_id=%s name=%s creator_id=%s",
            repository.id,
            repository.name,
            creator.id,
        )
        return repository

    async def get_repository(self, repository_id: int) -> Repository | None:
        return await self.uow.repositories.get(repository_id)

    async def list_repositories(self) -> list[Repository]:
        repositories, _ = await self.uow.repositories.list(limit=1000, offset=0)
        return list(repositories)

    async def update_repository(
        self,
        *,
        repository: Repository,
        description: str | None,
        visibility: RepositoryVisibility,
        allow_public_object_urls: bool,
    ) -> Repository:
        if repository.allow_public_object_urls != allow_public_object_urls:
            self._sync_public_object_access(
                repository_id=repository.id,
                allow_public_object_urls=allow_public_object_urls,
            )
        repository.description = description
        repository.visibility = visibility.value
        repository.allow_public_object_urls = allow_public_object_urls
        await self.uow.flush()
        await self.uow.commit()
        logger.info(
            "Repository updated repository_id=%s visibility=%s allow_public_object_urls=%s",
            repository.id,
            repository.visibility,
            repository.allow_public_object_urls,
        )
        return repository

    async def delete_repository(self, repository: Repository) -> Repository:
        memberships = await self.uow.repository_members.list_for_repository(repository.id)
        for membership in memberships:
            await self.uow.repository_members.delete(membership)
        await self.uow.repositories.delete(repository)
        await self.uow.commit()
        logger.info("Repository deleted repository_id=%s name=%s", repository.id, repository.name)
        return repository

    async def add_member(self, *, repository_id: int, user: User, role: Role) -> RepositoryMember:
        membership = await self.uow.repository_members.create(
            repository_id=repository_id,
            user_id=user.id,
            role_id=role.id,
        )
        await self.uow.commit()
        await self.uow.refresh(membership)
        refreshed_membership = await self.uow.repository_members.get_for_user_and_repository(
            user_id=user.id,
            repository_id=repository_id,
        )
        logger.info("Repository member added repository_id=%s user_id=%s role=%s", repository_id, user.id, role.name)
        return refreshed_membership or membership

    async def update_member_role(self, *, membership: RepositoryMember, role: Role) -> RepositoryMember:
        membership.role_id = role.id
        membership.role = role
        await self.uow.flush()
        await self.uow.commit()
        refreshed_membership = await self.uow.repository_members.get_for_user_and_repository(
            user_id=membership.user_id,
            repository_id=membership.repository_id,
        )
        logger.info(
            "Repository member updated repository_id=%s user_id=%s role=%s",
            membership.repository_id,
            membership.user_id,
            role.name,
        )
        return refreshed_membership or membership

    async def remove_member(self, membership: RepositoryMember) -> RepositoryMember:
        await self.uow.repository_members.delete(membership)
        await self.uow.commit()
        logger.info(
            "Repository member removed repository_id=%s user_id=%s",
            membership.repository_id,
            membership.user_id,
        )
        return membership

    @staticmethod
    def _sync_public_object_access(*, repository_id: int, allow_public_object_urls: bool) -> None:
        storage = storage_factory.get_storage_adapter()
        try:
            if allow_public_object_urls:
                storage.ensure_repository_public_access(repository_id=repository_id)
            else:
                storage.disable_repository_public_access(repository_id=repository_id)
        except Exception as error:
            raise UnprocessableEntityError(
                "Repository public object URL policy could not be updated",
                app_status=AppStatus.ERROR_UNPROCESSABLE_ENTITY,
            ) from error
