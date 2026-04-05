from dataclasses import dataclass

from cordis.backend.exceptions import AppStatus, ForbiddenOperationError, NotFoundError, UnauthorizedError
from cordis.backend.models import Repository, RepositoryMember, User
from cordis.backend.repositories.unit_of_work import UnitOfWork

ROLE_RANK = {"viewer": 1, "developer": 2, "owner": 3}


@dataclass(slots=True)
class RepositoryAccessContext:
    repository: Repository
    membership: RepositoryMember | None
    access: str


class AuthorizationService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def require_repository_access(
        self,
        *,
        repository_id: int,
        required_role: str,
        current_user: User | None,
    ) -> RepositoryAccessContext:
        repository = await self.uow.repositories.get(repository_id)
        if repository is None:
            raise NotFoundError("Repository not found", app_status=AppStatus.ERROR_REPOSITORY_NOT_FOUND)

        if current_user is not None and current_user.is_admin:
            return RepositoryAccessContext(repository=repository, membership=None, access=required_role)

        membership: RepositoryMember | None = None
        role_name: str | None = None
        if current_user is not None:
            membership = await self.uow.repository_members.get_for_user_and_repository(
                user_id=current_user.id,
                repository_id=repository_id,
            )
            if membership is not None and membership.role is not None:
                role_name = membership.role.name

        if required_role == "viewer" and repository.is_public:
            return RepositoryAccessContext(repository=repository, membership=membership, access="viewer")

        if current_user is None:
            raise UnauthorizedError("Missing bearer token", app_status=AppStatus.ERROR_MISSING_BEARER_TOKEN)

        if role_name is None:
            raise ForbiddenOperationError(
                "Repository access denied",
                app_status=AppStatus.ERROR_REPOSITORY_ACCESS_DENIED,
            )
        if ROLE_RANK[role_name] < ROLE_RANK[required_role]:
            raise ForbiddenOperationError(
                "Repository access denied",
                app_status=AppStatus.ERROR_REPOSITORY_ACCESS_DENIED,
            )

        return RepositoryAccessContext(repository=repository, membership=membership, access=required_role)
