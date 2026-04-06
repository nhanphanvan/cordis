from fastapi import FastAPI

from cordis import __version__
from cordis.backend.api import api_router, common_router
from cordis.backend.config import build_config
from cordis.backend.exceptions import configure_exception_handlers


def create_app() -> FastAPI:
    config = build_config()
    app = FastAPI(title=config.app.app_name, version=__version__)
    configure_exception_handlers(app)
    app.include_router(common_router)
    app.include_router(api_router)
    return app
