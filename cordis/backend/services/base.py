from typing import Any, Generic, TypeVar

from cordis.backend.models.base import DatabaseModel
from cordis.backend.repositories.base import BaseRepository
from cordis.backend.repositories.unit_of_work import UnitOfWork

ModelType = TypeVar("ModelType", bound=DatabaseModel)


class BaseService(Generic[ModelType]):
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def get_repository(self) -> BaseRepository[ModelType]:
        raise NotImplementedError

    async def get(self, entity_id: Any) -> ModelType | None:
        return await self.get_repository().get(entity_id)

    async def get_or_raise(self, entity_id: Any) -> ModelType:
        return await self.get_repository().get_or_raise(entity_id)

    async def list(self, limit: int = 100, offset: int = 0) -> tuple[list[ModelType], int]:
        items, total = await self.get_repository().list(limit=limit, offset=offset)
        return list(items), total
