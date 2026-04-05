from cordis.backend.models import User
from cordis.backend.validators.repository import RepositoryAccessContext


class ArtifactPolicy:
    @classmethod
    async def create(cls, _actor: User | None, context: RepositoryAccessContext) -> bool:
        return context.developer_allowed

    @classmethod
    async def read(cls, _actor: User | None, context: RepositoryAccessContext) -> bool:
        return context.viewer_allowed
