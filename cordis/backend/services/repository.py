import logging

from cordis.backend.exceptions import (
    AppStatus,
    InternalServerError,
    NotFoundError,
    NotUniqueError,
    UnprocessableEntityError,
)
from cordis.backend.models import Repository, RepositoryMember, User
from cordis.backend.repositories.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)


class RepositoryService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def create_repository(
        self,
        *,
        name: str,
        description: str | None,
        is_public: bool,
        creator: User,
    ) -> Repository:
        existing, _ = await self.uow.repositories.list(limit=1000, offset=0)
        if any(repository.name == name for repository in existing):
            raise NotUniqueError(
                "Repository name already exists",
                app_status=AppStatus.ERROR_REPOSITORY_NAME_ALREADY_EXISTS,
            )

        repository = await self.uow.repositories.create(name=name, description=description, is_public=is_public)
        owner_role = await self.uow.roles.get_by_name("owner")
        if owner_role is None:
            raise InternalServerError("Owner role is missing", app_status=AppStatus.ERROR_OWNER_ROLE_MISSING)

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

    async def get_repository(self, repository_id: int) -> Repository:
        repository = await self.uow.repositories.get(repository_id)
        if repository is None:
            raise NotFoundError("Repository not found", app_status=AppStatus.ERROR_REPOSITORY_NOT_FOUND)
        return repository

    async def list_repositories(self) -> list[Repository]:
        repositories, _ = await self.uow.repositories.list(limit=1000, offset=0)
        return list(repositories)

    async def update_repository(
        self,
        *,
        repository_id: int,
        description: str | None,
        is_public: bool,
    ) -> Repository:
        repository = await self.get_repository(repository_id)
        repository.description = description
        repository.is_public = is_public
        await self.uow.flush()
        await self.uow.commit()
        logger.info("Repository updated repository_id=%s is_public=%s", repository.id, repository.is_public)
        return repository

    async def delete_repository(self, repository_id: int) -> Repository:
        repository = await self.get_repository(repository_id)
        memberships = await self.uow.repository_members.list_for_repository(repository_id)
        for membership in memberships:
            await self.uow.repository_members.delete(membership)
        await self.uow.repositories.delete(repository)
        await self.uow.commit()
        logger.info("Repository deleted repository_id=%s name=%s", repository.id, repository.name)
        return repository

    async def add_member(self, *, repository_id: int, user_id: int, role_name: str) -> RepositoryMember:
        existing = await self.uow.repository_members.get_for_user_and_repository(
            user_id=user_id,
            repository_id=repository_id,
        )
        if existing is not None:
            raise NotUniqueError(
                "Repository member already exists",
                app_status=AppStatus.ERROR_REPOSITORY_MEMBER_ALREADY_EXISTS,
            )

        user = await self.uow.users.get(user_id)
        if user is None:
            raise NotFoundError("User not found", app_status=AppStatus.ERROR_USER_NOT_FOUND)
        role = await self.uow.roles.get_by_name(role_name)
        if role is None:
            raise UnprocessableEntityError(
                "Invalid repository role",
                app_status=AppStatus.ERROR_REPOSITORY_ROLE_INVALID,
            )

        membership = await self.uow.repository_members.create(
            repository_id=repository_id,
            user_id=user_id,
            role_id=role.id,
        )
        await self.uow.commit()
        await self.uow.refresh(membership)
        refreshed_membership = await self.uow.repository_members.get_for_user_and_repository(
            user_id=user_id,
            repository_id=repository_id,
        )
        logger.info("Repository member added repository_id=%s user_id=%s role=%s", repository_id, user_id, role_name)
        return refreshed_membership or membership

    async def update_member_role(self, *, repository_id: int, user_id: int, role_name: str) -> RepositoryMember:
        membership = await self.uow.repository_members.get_for_user_and_repository(
            user_id=user_id,
            repository_id=repository_id,
        )
        if membership is None:
            raise NotFoundError("Repository member not found", app_status=AppStatus.ERROR_REPOSITORY_MEMBER_NOT_FOUND)
        role = await self.uow.roles.get_by_name(role_name)
        if role is None:
            raise UnprocessableEntityError(
                "Invalid repository role",
                app_status=AppStatus.ERROR_REPOSITORY_ROLE_INVALID,
            )

        membership.role_id = role.id
        membership.role = role
        await self.uow.flush()
        await self.uow.commit()
        refreshed_membership = await self.uow.repository_members.get_for_user_and_repository(
            user_id=user_id,
            repository_id=repository_id,
        )
        logger.info("Repository member updated repository_id=%s user_id=%s role=%s", repository_id, user_id, role_name)
        return refreshed_membership or membership

    async def remove_member(self, *, repository_id: int, user_id: int) -> RepositoryMember:
        membership = await self.uow.repository_members.get_for_user_and_repository(
            user_id=user_id,
            repository_id=repository_id,
        )
        if membership is None:
            raise NotFoundError("Repository member not found", app_status=AppStatus.ERROR_REPOSITORY_MEMBER_NOT_FOUND)
        await self.uow.repository_members.delete(membership)
        await self.uow.commit()
        logger.info("Repository member removed repository_id=%s user_id=%s", repository_id, user_id)
        return membership
