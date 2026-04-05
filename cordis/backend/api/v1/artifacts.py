from typing import Annotated

from fastapi import APIRouter, Depends

from cordis.backend.api.dependencies import get_current_user, get_optional_current_user, get_uow
from cordis.backend.exceptions import AppStatus
from cordis.backend.models import User
from cordis.backend.policies import ArtifactPolicy, authorize
from cordis.backend.repositories.unit_of_work import UnitOfWork
from cordis.backend.schemas.requests.artifact import ArtifactCreateRequest
from cordis.backend.schemas.responses.artifact import ArtifactResponse
from cordis.backend.services.artifact import ArtifactService
from cordis.backend.validators.artifact import ArtifactCreateValidator, ArtifactReadValidator
from cordis.backend.validators.repository import RepositoryAccessValidator

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


def _artifact_response(
    artifact_id: str,
    repository_id: int,
    path: str,
    name: str,
    checksum: str,
    size: int,
) -> ArtifactResponse:
    return ArtifactResponse(
        id=artifact_id,
        repository_id=repository_id,
        path=path,
        name=name,
        checksum=checksum,
        size=size,
    )


@router.post("", response_model=ArtifactResponse, status_code=201)
async def create_artifact(
    request: ArtifactCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> ArtifactResponse:
    artifact_input = await ArtifactCreateValidator.validate(uow=uow, request=request)
    access = await RepositoryAccessValidator.validate(
        uow=uow,
        repository_id=artifact_input.repository.id,
        current_user=current_user,
    )
    await authorize(current_user, ArtifactPolicy.create, access)
    artifact = await ArtifactService(uow).create_artifact(
        repository=artifact_input.repository,
        path=artifact_input.normalized_path,
        name=artifact_input.name,
        checksum=artifact_input.checksum,
        size=artifact_input.size,
    )
    return _artifact_response(
        artifact.id,
        artifact.repository_id,
        artifact.path,
        artifact.name,
        artifact.checksum,
        artifact.size,
    )


@router.get("/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(
    artifact_id: str,
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> ArtifactResponse:
    artifact = await ArtifactReadValidator.validate(uow=uow, artifact_id=artifact_id)
    access = await RepositoryAccessValidator.validate(
        uow=uow,
        repository_id=artifact.repository_id,
        current_user=current_user,
    )
    await authorize(
        current_user,
        ArtifactPolicy.read,
        access,
        unauthorized_message="Missing bearer token",
        unauthorized_app_status=AppStatus.ERROR_MISSING_BEARER_TOKEN,
    )
    return _artifact_response(
        artifact.id,
        artifact.repository_id,
        artifact.path,
        artifact.name,
        artifact.checksum,
        artifact.size,
    )
