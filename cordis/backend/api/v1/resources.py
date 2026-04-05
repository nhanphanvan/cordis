from typing import Annotated

from fastapi import APIRouter, Depends

from cordis.backend.api.dependencies import get_current_user, get_uow
from cordis.backend.models import User
from cordis.backend.repositories.unit_of_work import UnitOfWork
from cordis.backend.schemas.artifact import ResourceCheckRequest, ResourceCheckResponse
from cordis.backend.services.authorization import AuthorizationService
from cordis.backend.services.version import VersionService
from cordis.backend.services.version_artifact import VersionArtifactService

router = APIRouter(prefix="/resources", tags=["resources"])


@router.post("/check", response_model=ResourceCheckResponse)
async def check_resource(
    request: ResourceCheckRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> ResourceCheckResponse:
    version = await VersionService(uow).get_version(request.version_id)
    await AuthorizationService(uow).require_repository_access(
        repository_id=version.repository_id,
        required_role="developer",
        current_user=current_user,
    )
    status, artifact_id = await VersionArtifactService(uow).check_resource(
        version_id=request.version_id,
        path=request.path,
        checksum=request.checksum,
        size=request.size,
    )
    return ResourceCheckResponse(status=status, artifact_id=artifact_id)
