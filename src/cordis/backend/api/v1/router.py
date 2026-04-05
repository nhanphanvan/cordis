from fastapi import APIRouter

from cordis.backend.api.v1.artifacts import router as artifacts_router
from cordis.backend.api.v1.auth import router as auth_router
from cordis.backend.api.v1.repositories import router as repositories_router
from cordis.backend.api.v1.resources import router as resources_router
from cordis.backend.api.v1.roles import admin_router as admin_roles_router
from cordis.backend.api.v1.roles import router as roles_router
from cordis.backend.api.v1.tags import router as tags_router
from cordis.backend.api.v1.uploads import router as uploads_router
from cordis.backend.api.v1.users import admin_router as admin_users_router
from cordis.backend.api.v1.users import router as users_router
from cordis.backend.api.v1.versions import router as versions_router

router = APIRouter(prefix="/api/v1")


@router.get("/healthz")
async def healthcheck_v1() -> dict[str, str]:
    return {"status": "ok"}


router.include_router(auth_router)
router.include_router(artifacts_router)
router.include_router(repositories_router)
router.include_router(roles_router)
router.include_router(resources_router)
router.include_router(tags_router)
router.include_router(uploads_router)
router.include_router(users_router)
router.include_router(versions_router)
router.include_router(admin_users_router)
router.include_router(admin_roles_router)
