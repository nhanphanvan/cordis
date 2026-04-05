from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from cordis.backend.database import get_async_session
from cordis.backend.repositories.unit_of_work import UnitOfWork, get_unit_of_work


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_async_session():
        yield session


async def get_uow() -> AsyncGenerator[UnitOfWork, None]:
    async with get_unit_of_work() as uow:
        yield uow
