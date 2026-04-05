from typing import Annotated

from fastapi import APIRouter, Depends, Query

from cordis.backend.api.dependencies import (
    get_current_user,
    get_optional_current_user,
    get_uow,
)
from cordis.backend.models import User
from cordis.backend.repositories.unit_of_work import UnitOfWork
from cordis.backend.schemas.requests.artifact import VersionArtifactCreateRequest
from cordis.backend.schemas.requests.version import VersionCreateRequest
from cordis.backend.schemas.responses.artifact import (
    ArtifactDownloadResponse,
    ArtifactListResponse,
    ArtifactResponse,
)
from cordis.backend.schemas.responses.version import VersionResponse
from cordis.backend.services.authorization import AuthorizationService
from cordis.backend.services.download import DownloadService
from cordis.backend.services.version import VersionService
from cordis.backend.services.version_artifact import VersionArtifactService

router = APIRouter(prefix="/versions", tags=["versions"])


def _version_response(version_id: str, repository_id: int, name: str) -> VersionResponse:
    return VersionResponse(id=version_id, repository_id=repository_id, name=name)


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


@router.post("", response_model=VersionResponse, status_code=201)
async def create_version(
    request: VersionCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> VersionResponse:
    await AuthorizationService(uow).require_repository_access(
        repository_id=request.repository_id,
        required_role="developer",
        current_user=current_user,
    )
    version = await VersionService(uow).create_version(repository_id=request.repository_id, name=request.name)
    return _version_response(version.id, version.repository_id, version.name)


@router.get("/{version_id}", response_model=VersionResponse)
async def get_version(
    version_id: str,
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> VersionResponse:
    version = await VersionService(uow).get_version(version_id)
    await AuthorizationService(uow).require_repository_access(
        repository_id=version.repository_id,
        required_role="viewer",
        current_user=current_user,
    )
    return _version_response(version.id, version.repository_id, version.name)


@router.get("", response_model=VersionResponse)
async def lookup_version(
    repository_id: Annotated[int, Query()],
    name: Annotated[str, Query()],
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> VersionResponse:
    await AuthorizationService(uow).require_repository_access(
        repository_id=repository_id,
        required_role="viewer",
        current_user=current_user,
    )
    version = await VersionService(uow).get_by_repository_and_name(repository_id=repository_id, name=name)
    return _version_response(version.id, version.repository_id, version.name)


@router.delete("/{version_id}", response_model=VersionResponse)
async def delete_version(
    version_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> VersionResponse:
    version = await VersionService(uow).get_version(version_id)
    await AuthorizationService(uow).require_repository_access(
        repository_id=version.repository_id,
        required_role="developer",
        current_user=current_user,
    )
    deleted = await VersionService(uow).delete_version(version_id)
    return _version_response(deleted.id, deleted.repository_id, deleted.name)


@router.post("/{version_id}/artifacts", response_model=ArtifactResponse, status_code=201)
async def attach_artifact_to_version(
    version_id: str,
    request: VersionArtifactCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> ArtifactResponse:
    version = await VersionService(uow).get_version(version_id)
    await AuthorizationService(uow).require_repository_access(
        repository_id=version.repository_id,
        required_role="developer",
        current_user=current_user,
    )
    artifact = await VersionArtifactService(uow).attach_artifact(version_id=version_id, artifact_id=request.artifact_id)
    return _artifact_response(
        artifact.id,
        artifact.repository_id,
        artifact.path,
        artifact.name,
        artifact.checksum,
        artifact.size,
    )


@router.get("/{version_id}/artifacts", response_model=ArtifactListResponse)
async def list_version_artifacts(
    version_id: str,
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> ArtifactListResponse:
    version = await VersionService(uow).get_version(version_id)
    await AuthorizationService(uow).require_repository_access(
        repository_id=version.repository_id,
        required_role="viewer",
        current_user=current_user,
    )
    artifacts = await VersionArtifactService(uow).list_for_version(version_id)
    return ArtifactListResponse(
        items=[
            _artifact_response(
                artifact.id,
                artifact.repository_id,
                artifact.path,
                artifact.name,
                artifact.checksum,
                artifact.size,
            )
            for artifact in artifacts
        ]
    )


@router.get("/{version_id}/artifacts/by-path", response_model=ArtifactResponse)
async def get_version_artifact_by_path(
    version_id: str,
    path: Annotated[str, Query()],
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> ArtifactResponse:
    version = await VersionService(uow).get_version(version_id)
    await AuthorizationService(uow).require_repository_access(
        repository_id=version.repository_id,
        required_role="viewer",
        current_user=current_user,
    )
    artifact = await DownloadService(uow).get_artifact_for_version_by_path(version_id=version_id, path=path)
    return _artifact_response(
        artifact.id,
        artifact.repository_id,
        artifact.path,
        artifact.name,
        artifact.checksum,
        artifact.size,
    )


@router.post("/{version_id}/artifacts/{artifact_id}/download", response_model=ArtifactDownloadResponse)
async def create_version_artifact_download(
    version_id: str,
    artifact_id: str,
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> ArtifactDownloadResponse:
    version = await VersionService(uow).get_version(version_id)
    await AuthorizationService(uow).require_repository_access(
        repository_id=version.repository_id,
        required_role="viewer",
        current_user=current_user,
    )
    download_url, expires_in = await DownloadService(uow).get_download_url(
        version_id=version_id,
        artifact_id=artifact_id,
    )
    return ArtifactDownloadResponse(
        artifact_id=artifact_id,
        download_url=download_url,
        expires_in=expires_in,
    )
