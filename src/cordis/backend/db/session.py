from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from cordis.shared.settings import Settings, get_settings


def build_async_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(settings.db_url, echo=settings.db_echo, future=True)


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    return build_async_engine(get_settings())


@lru_cache(maxsize=1)
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=get_engine(), expire_on_commit=False, class_=AsyncSession)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session
