from collections.abc import Sequence
from typing import Any, Generic, Protocol, TypeVar, cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cordis.backend.db.base import ModelBase
from cordis.backend.errors import NotFoundError, ValidationError


class HasPrimaryKey(Protocol):
    id: Any


ModelType = TypeVar("ModelType", bound=ModelBase)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def create(self, **values: Any) -> ModelType:
        instance = self.model(**values)
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def get(self, entity_id: Any) -> ModelType | None:
        model_with_id = cast(type[HasPrimaryKey], self.model)
        result = await self.session.execute(select(self.model).where(model_with_id.id == entity_id))
        return result.scalar_one_or_none()

    async def get_or_raise(self, entity_id: Any) -> ModelType:
        instance = await self.get(entity_id)
        if instance is None:
            raise NotFoundError(f"{self.model.__name__} `{entity_id}` was not found")
        return instance

    async def list(self, limit: int = 100, offset: int = 0) -> tuple[Sequence[ModelType], int]:
        if limit < 0 or offset < 0:
            raise ValidationError("limit and offset must be non-negative")

        items = (await self.session.execute(select(self.model).limit(limit).offset(offset))).scalars().all()
        total = await self.session.scalar(select(func.count()).select_from(self.model))  # pylint: disable=not-callable
        return items, int(total or 0)

    async def delete(self, instance: ModelType) -> None:
        await self.session.delete(instance)
        await self.session.flush()
