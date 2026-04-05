from cordis.backend.models import User
from cordis.backend.validators.repository import RepositoryAccessContext


class DownloadPolicy:
    @classmethod
    async def read(cls, _actor: User | None, context: RepositoryAccessContext) -> bool:
        return context.viewer_allowed
