from cordis.backend.models import User
from cordis.backend.validators.repository import RepositoryAccessContext


class UploadPolicy:
    @classmethod
    async def mutate(cls, _actor: User | None, context: RepositoryAccessContext) -> bool:
        return context.developer_allowed
