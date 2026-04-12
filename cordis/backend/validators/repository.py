from dataclasses import dataclass

from cordis.backend.constants import BUILTIN_OWNER_ROLE, ROLE_RANK
from cordis.backend.enums import RepositoryAccessRole, RepositoryVisibility
from cordis.backend.exceptions import (
    AppStatus,
    InternalServerError,
    NotFoundError,
    NotUniqueError,
    UnauthorizedError,
    UnprocessableEntityError,
)
from cordis.backend.models import Repository, RepositoryMember, Role, User
from cordis.backend.repositories.unit_of_work import UnitOfWork
from cordis.backend.schemas.requests.repository import (
    RepositoryCreateRequest,
    RepositoryMemberMutationRequest,
    RepositoryMemberRoleUpdateRequest,
)

from .base import BaseValidator


@dataclass(slots=True)
class RepositoryAccessContext:
    repository: Repository
    membership: RepositoryMember | None
    role_name: RepositoryAccessRole | None
    viewer_allowed: bool
    developer_allowed: bool
    owner_allowed: bool


class RepositoryAccessValidator(BaseValidator):
    @classmethod
    async def validate(
        cls,
        *,
        uow: UnitOfWork,
        repository_id: int,
        current_user: User | None,
    ) -> RepositoryAccessContext:
        repository = await uow.repositories.get(repository_id)
        if repository is None:
            raise NotFoundError("Repository not found", app_status=AppStatus.ERROR_REPOSITORY_NOT_FOUND)

        membership: RepositoryMember | None = None
        role_name: RepositoryAccessRole | None = None
        if current_user is not None and current_user.is_admin:
            return RepositoryAccessContext(
                repository=repository,
                membership=None,
                role_name=RepositoryAccessRole.OWNER,
                viewer_allowed=True,
                developer_allowed=True,
                owner_allowed=True,
            )

        if current_user is not None:
            membership = await uow.repository_members.get_for_user_and_repository(
                user_id=current_user.id,
                repository_id=repository_id,
            )
            if membership is not None and membership.role is not None:
                try:
                    role_name = RepositoryAccessRole(membership.role.name)
                except ValueError:
                    role_name = None

        viewer_allowed = (
            current_user is not None and repository.visibility == RepositoryVisibility.AUTHENTICATED.value
        ) or (role_name is not None and ROLE_RANK[role_name] >= ROLE_RANK[RepositoryAccessRole.VIEWER])
        developer_allowed = role_name is not None and ROLE_RANK[role_name] >= ROLE_RANK[RepositoryAccessRole.DEVELOPER]
        owner_allowed = role_name is not None and ROLE_RANK[role_name] >= ROLE_RANK[RepositoryAccessRole.OWNER]

        return RepositoryAccessContext(
            repository=repository,
            membership=membership,
            role_name=role_name,
            viewer_allowed=viewer_allowed,
            developer_allowed=developer_allowed,
            owner_allowed=owner_allowed,
        )


class RepositoryCreateValidator(BaseValidator):
    @classmethod
    async def validate(cls, *, uow: UnitOfWork, request: RepositoryCreateRequest) -> Role:
        existing, _ = await uow.repositories.list(limit=1000, offset=0)
        if any(repository.name == request.name for repository in existing):
            raise NotUniqueError(
                "Repository name already exists",
                app_status=AppStatus.ERROR_REPOSITORY_NAME_ALREADY_EXISTS,
            )
        owner_role = await uow.roles.get_by_name(BUILTIN_OWNER_ROLE.value)
        if owner_role is None:
            raise InternalServerError("Owner role is missing", app_status=AppStatus.ERROR_OWNER_ROLE_MISSING)
        return owner_role


class RepositoryMemberCreateValidator(BaseValidator):
    @classmethod
    async def validate(
        cls,
        *,
        uow: UnitOfWork,
        repository_id: int,
        request: RepositoryMemberMutationRequest,
    ) -> tuple[User, Role]:
        existing = await uow.repository_members.get_for_user_and_repository(
            user_id=request.user_id,
            repository_id=repository_id,
        )
        if existing is not None:
            raise NotUniqueError(
                "Repository member already exists",
                app_status=AppStatus.ERROR_REPOSITORY_MEMBER_ALREADY_EXISTS,
            )
        user = await uow.users.get(request.user_id)
        if user is None:
            raise NotFoundError("User not found", app_status=AppStatus.ERROR_USER_NOT_FOUND)
        role = await uow.roles.get_by_name(request.role)
        if role is None:
            raise UnprocessableEntityError(
                "Invalid repository role",
                app_status=AppStatus.ERROR_REPOSITORY_ROLE_INVALID,
            )
        return user, role


class RepositoryMemberRoleUpdateValidator(BaseValidator):
    @classmethod
    async def validate(
        cls,
        *,
        uow: UnitOfWork,
        repository_id: int,
        user_id: int,
        request: RepositoryMemberRoleUpdateRequest,
    ) -> tuple[RepositoryMember, Role]:
        membership = await uow.repository_members.get_for_user_and_repository(
            user_id=user_id,
            repository_id=repository_id,
        )
        if membership is None:
            raise NotFoundError("Repository member not found", app_status=AppStatus.ERROR_REPOSITORY_MEMBER_NOT_FOUND)
        role = await uow.roles.get_by_name(request.role)
        if role is None:
            raise UnprocessableEntityError(
                "Invalid repository role",
                app_status=AppStatus.ERROR_REPOSITORY_ROLE_INVALID,
            )
        return membership, role


class RepositoryMemberDeleteValidator(BaseValidator):
    @classmethod
    async def validate(cls, *, uow: UnitOfWork, repository_id: int, user_id: int) -> RepositoryMember:
        membership = await uow.repository_members.get_for_user_and_repository(
            user_id=user_id,
            repository_id=repository_id,
        )
        if membership is None:
            raise NotFoundError("Repository member not found", app_status=AppStatus.ERROR_REPOSITORY_MEMBER_NOT_FOUND)
        return membership


class BearerUserRequiredValidator(BaseValidator):
    @classmethod
    async def validate(cls, *, current_user: User | None) -> User:
        if current_user is None:
            raise UnauthorizedError("Missing bearer token", app_status=AppStatus.ERROR_MISSING_BEARER_TOKEN)
        return current_user
