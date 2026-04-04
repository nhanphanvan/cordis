from fastapi import FastAPI

from cordis.backend.api import router
from cordis.shared.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)
    app.include_router(router)
    return app
