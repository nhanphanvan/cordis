from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from cordis import __version__
from cordis.backend.api import api_router, common_router
from cordis.backend.bootstrap import bootstrap_runtime_state
from cordis.backend.config import build_config
from cordis.backend.exceptions import configure_exception_handlers


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await bootstrap_runtime_state()
    yield


def create_app() -> FastAPI:
    config = build_config()
    app = FastAPI(title=config.app.app_name, version=__version__, lifespan=lifespan)
    configure_exception_handlers(app)
    app.include_router(common_router)
    app.include_router(api_router)
    return app
