from fastapi import FastAPI

from cordis import __version__
from cordis.backend.api import common_router, register_exception_handlers, v1_router
from cordis.shared.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=__version__)
    register_exception_handlers(app)
    app.include_router(common_router)
    app.include_router(v1_router)
    return app
