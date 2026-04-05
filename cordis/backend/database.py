from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from cordis.backend.config import DatabaseConfig, build_config


def build_async_engine(config: DatabaseConfig) -> AsyncEngine:
    return create_async_engine(
        config.db_url,
        echo=config.db_echo,
        future=True,
        **config.database_engine_args,
    )


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    return build_async_engine(build_config().database)


@lru_cache(maxsize=1)
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=get_engine(), expire_on_commit=False, class_=AsyncSession)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session
