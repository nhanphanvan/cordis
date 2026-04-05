from fastapi import APIRouter

from cordis.shared.settings import get_settings
from cordis.shared.version import get_version_payload

router = APIRouter()


@router.get("/healthz")
async def healthcheck() -> dict[str, str]:
    settings = get_settings()
    return {"service": settings.app_name, "status": "ok"}


@router.get("/version")
async def version() -> dict[str, str]:
    return get_version_payload()
