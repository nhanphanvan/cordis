from fastapi import APIRouter

from cordis.backend.config import build_config
from cordis.backend.versioning import get_version_payload

router = APIRouter()


@router.get("/healthz")
async def healthcheck() -> dict[str, str]:
    config = build_config()
    return {"service": config.app.app_name, "status": "ok"}


@router.get("/version")
async def version() -> dict[str, str]:
    return get_version_payload()
