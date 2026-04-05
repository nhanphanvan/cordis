from typing import Annotated

from fastapi import APIRouter, Depends

from cordis.backend.api.dependencies import get_current_user, get_optional_current_user, get_uow
from cordis.backend.models import User
from cordis.backend.repositories.unit_of_work import UnitOfWork
from cordis.backend.schemas.artifact import ArtifactCreateRequest, ArtifactResponse
from cordis.backend.services.artifact import ArtifactService
from cordis.backend.services.authorization import AuthorizationService

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
    await AuthorizationService(uow).require_repository_access(
        repository_id=request.repository_id,
        required_role="developer",
        current_user=current_user,
    )
    artifact = await ArtifactService(uow).create_artifact(
        repository_id=request.repository_id,
        path=request.path,
        checksum=request.checksum,
        size=request.size,
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
    artifact = await ArtifactService(uow).get_artifact(artifact_id)
    await AuthorizationService(uow).require_repository_access(
        repository_id=artifact.repository_id,
        required_role="viewer",
        current_user=current_user,
    )
    return _artifact_response(
        artifact.id,
        artifact.repository_id,
        artifact.path,
        artifact.name,
        artifact.checksum,
        artifact.size,
    )
