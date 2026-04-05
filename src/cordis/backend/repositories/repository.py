from sqlalchemy.ext.asyncio import AsyncSession

from cordis.backend.models import Repository
from cordis.backend.repositories.base import BaseRepository


class RepositoryRepository(BaseRepository[Repository]):
    def __init__(self, session: AsyncSession):
        super().__init__(Repository, session)
