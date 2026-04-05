from cordis.backend.models import Repository, RepositoryMember, User
from cordis.backend.repositories.unit_of_work import UnitOfWork
from cordis.shared.errors import ConflictError, NotFoundError, ValidationError


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
            raise ConflictError("Repository name already exists")

        repository = await self.uow.repositories.create(name=name, description=description, is_public=is_public)
        owner_role = await self.uow.roles.get_by_name("owner")
        if owner_role is None:
            raise ValidationError("Owner role is missing")

        await self.uow.repository_members.create(
            repository_id=repository.id,
            user_id=creator.id,
            role_id=owner_role.id,
        )
        await self.uow.commit()
        await self.uow.refresh(repository)
        return repository

    async def get_repository(self, repository_id: int) -> Repository:
        repository = await self.uow.repositories.get(repository_id)
        if repository is None:
            raise NotFoundError("Repository not found")
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
        return repository

    async def delete_repository(self, repository_id: int) -> Repository:
        repository = await self.get_repository(repository_id)
        memberships = await self.uow.repository_members.list_for_repository(repository_id)
        for membership in memberships:
            await self.uow.repository_members.delete(membership)
        await self.uow.repositories.delete(repository)
        await self.uow.commit()
        return repository

    async def add_member(self, *, repository_id: int, user_id: int, role_name: str) -> RepositoryMember:
        existing = await self.uow.repository_members.get_for_user_and_repository(
            user_id=user_id,
            repository_id=repository_id,
        )
        if existing is not None:
            raise ConflictError("Repository member already exists")

        user = await self.uow.users.get(user_id)
        if user is None:
            raise NotFoundError("User not found")
        role = await self.uow.roles.get_by_name(role_name)
        if role is None:
            raise ValidationError("Invalid repository role")

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
        return refreshed_membership or membership

    async def update_member_role(self, *, repository_id: int, user_id: int, role_name: str) -> RepositoryMember:
        membership = await self.uow.repository_members.get_for_user_and_repository(
            user_id=user_id,
            repository_id=repository_id,
        )
        if membership is None:
            raise NotFoundError("Repository member not found")
        role = await self.uow.roles.get_by_name(role_name)
        if role is None:
            raise ValidationError("Invalid repository role")

        membership.role_id = role.id
        membership.role = role
        await self.uow.flush()
        await self.uow.commit()
        refreshed_membership = await self.uow.repository_members.get_for_user_and_repository(
            user_id=user_id,
            repository_id=repository_id,
        )
        return refreshed_membership or membership

    async def remove_member(self, *, repository_id: int, user_id: int) -> RepositoryMember:
        membership = await self.uow.repository_members.get_for_user_and_repository(
            user_id=user_id,
            repository_id=repository_id,
        )
        if membership is None:
            raise NotFoundError("Repository member not found")
        await self.uow.repository_members.delete(membership)
        await self.uow.commit()
        return membership
