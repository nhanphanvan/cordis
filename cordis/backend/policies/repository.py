from cordis.backend.models import User
from cordis.backend.validators.repository import RepositoryAccessContext


class RepositoryPolicy:
    @classmethod
    async def create(cls, actor: User | None) -> bool:
        return actor is not None and actor.is_admin

    @classmethod
    async def list(cls, actor: User | None) -> bool:
        return actor is not None and actor.is_admin

    @classmethod
    async def viewer(cls, _actor: User | None, context: RepositoryAccessContext) -> bool:
        return context.viewer_allowed

    @classmethod
    async def developer(cls, _actor: User | None, context: RepositoryAccessContext) -> bool:
        return context.developer_allowed

    @classmethod
    async def owner(cls, _actor: User | None, context: RepositoryAccessContext) -> bool:
        return context.owner_allowed
