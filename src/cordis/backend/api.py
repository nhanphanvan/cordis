from fastapi import APIRouter

from cordis import __version__
from cordis.shared.settings import get_settings

router = APIRouter()


@router.get("/healthz")
def healthcheck() -> dict[str, str]:
    settings = get_settings()
    return {"service": settings.app_name, "status": "ok"}


@router.get("/version")
def version() -> dict[str, str]:
    return {"version": __version__}
