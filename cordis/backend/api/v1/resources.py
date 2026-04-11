from typing import Annotated

from fastapi import APIRouter, Depends

from cordis.backend.api.dependencies import get_current_user, get_uow
from cordis.backend.models import User
from cordis.backend.policies import VersionPolicy, authorize
from cordis.backend.repositories.unit_of_work import UnitOfWork
from cordis.backend.schemas.requests.artifact import ResourceCheckRequest
from cordis.backend.schemas.responses.artifact import ResourceCheckResponse
from cordis.backend.services.version_artifact import VersionArtifactService
from cordis.backend.validators.artifact import ResourceCheckValidator
from cordis.backend.validators.repository import RepositoryAccessValidator

router = APIRouter(prefix="/resources", tags=["resources"])


@router.post("/check", response_model=ResourceCheckResponse)
async def check_resource(
    request: ResourceCheckRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> ResourceCheckResponse:
    version = await ResourceCheckValidator.validate(uow=uow, request=request)
    access = await RepositoryAccessValidator.validate(
        uow=uow,
        repository_id=version.repository_id,
        current_user=current_user,
    )
    await authorize(current_user, VersionPolicy.create, access)
    resource_status, artifact_id = await VersionArtifactService(uow).check_resource(
        version_id=request.version_id,
        path=request.path,
        checksum=request.checksum,
        size=request.size,
    )
    return ResourceCheckResponse(status=resource_status, artifact_id=artifact_id)
