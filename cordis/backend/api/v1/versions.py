from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from cordis.backend.api.dependencies import (
    get_current_user,
    get_optional_current_user,
    get_uow,
)
from cordis.backend.exceptions import AppStatus
from cordis.backend.models import User
from cordis.backend.policies import DownloadPolicy, VersionPolicy, authorize
from cordis.backend.repositories.unit_of_work import UnitOfWork
from cordis.backend.schemas.requests.artifact import VersionArtifactCreateRequest, VersionArtifactPathClearRequest
from cordis.backend.schemas.requests.version import VersionCreateRequest
from cordis.backend.schemas.responses.artifact import (
    ArtifactDownloadResponse,
    ArtifactListResponse,
    ArtifactResponse,
    VersionArtifactClearResponse,
)
from cordis.backend.schemas.responses.version import VersionResponse
from cordis.backend.services.download import DownloadService
from cordis.backend.services.version import VersionService
from cordis.backend.services.version_artifact import VersionArtifactService
from cordis.backend.storage import StorageObjectRef
from cordis.backend.storage import factory as storage_factory
from cordis.backend.validators.artifact import VersionArtifactAttachValidator
from cordis.backend.validators.download import VersionArtifactPathReadValidator, VersionArtifactReadValidator
from cordis.backend.validators.repository import RepositoryAccessValidator
from cordis.backend.validators.version import VersionCreateValidator, VersionLookupValidator, VersionReadValidator

router = APIRouter(prefix="/versions", tags=["versions"])


def _version_response(version_id: UUID, repository_id: int, name: str, description: str | None) -> VersionResponse:
    return VersionResponse(id=version_id, repository_id=repository_id, name=name, description=description)


def _artifact_response(
    artifact_id: UUID,
    repository_id: int,
    path: str,
    name: str,
    checksum: str,
    size: int,
    public_url: str | None,
) -> ArtifactResponse:
    return ArtifactResponse(
        id=artifact_id,
        repository_id=repository_id,
        path=path,
        name=name,
        checksum=checksum,
        size=size,
        public_url=public_url,
    )


def _build_public_url(
    *,
    repository_id: int,
    artifact_id: UUID,
    path: str,
    allow_public_object_urls: bool,
) -> str | None:
    if not allow_public_object_urls:
        return None
    return storage_factory.get_storage_adapter().get_public_url(
        StorageObjectRef(repository_id=repository_id, artifact_id=artifact_id, path=path),
    )


@router.post("", response_model=VersionResponse, status_code=201)
async def create_version(
    request: VersionCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> VersionResponse:
    repository = await VersionCreateValidator.validate(uow=uow, request=request)
    access = await RepositoryAccessValidator.validate(uow=uow, repository_id=repository.id, current_user=current_user)
    await authorize(current_user, VersionPolicy.create, access)
    version = await VersionService(uow).create_version(
        repository=repository,
        name=request.name,
        description=request.description,
    )
    return _version_response(version.id, version.repository_id, version.name, version.description)


@router.get("/{version_id}", response_model=VersionResponse)
async def get_version(
    version_id: UUID,
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> VersionResponse:
    version = await VersionReadValidator.validate(uow=uow, version_id=version_id)
    access = await RepositoryAccessValidator.validate(
        uow=uow,
        repository_id=version.repository_id,
        current_user=current_user,
    )
    await authorize(
        current_user,
        VersionPolicy.read,
        access,
        unauthorized_message="Missing bearer token",
        unauthorized_app_status=AppStatus.ERROR_MISSING_BEARER_TOKEN,
    )
    return _version_response(version.id, version.repository_id, version.name, version.description)


@router.get("", response_model=VersionResponse)
async def lookup_version(
    repository_id: Annotated[int, Query()],
    name: Annotated[str, Query()],
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> VersionResponse:
    access = await RepositoryAccessValidator.validate(uow=uow, repository_id=repository_id, current_user=current_user)
    await authorize(
        current_user,
        VersionPolicy.read,
        access,
        unauthorized_message="Missing bearer token",
        unauthorized_app_status=AppStatus.ERROR_MISSING_BEARER_TOKEN,
    )
    version = await VersionLookupValidator.validate(uow=uow, repository_id=repository_id, name=name)
    return _version_response(version.id, version.repository_id, version.name, version.description)


@router.delete("/{version_id}", response_model=VersionResponse)
async def delete_version(
    version_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> VersionResponse:
    version = await VersionReadValidator.validate(uow=uow, version_id=version_id)
    access = await RepositoryAccessValidator.validate(
        uow=uow,
        repository_id=version.repository_id,
        current_user=current_user,
    )
    await authorize(current_user, VersionPolicy.delete, access)
    deleted = await VersionService(uow).delete_version(version)
    return _version_response(deleted.id, deleted.repository_id, deleted.name, deleted.description)


@router.post("/{version_id}/artifacts", response_model=ArtifactResponse, status_code=201)
async def attach_artifact_to_version(
    version_id: UUID,
    request: VersionArtifactCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> ArtifactResponse:
    version = await VersionReadValidator.validate(uow=uow, version_id=version_id)
    access = await RepositoryAccessValidator.validate(
        uow=uow,
        repository_id=version.repository_id,
        current_user=current_user,
    )
    await authorize(current_user, VersionPolicy.create, access)
    artifact = await VersionArtifactAttachValidator.validate(
        uow=uow,
        version=version,
        request=request,
    )
    artifact = await VersionArtifactService(uow).attach_artifact(version=version, artifact=artifact)
    return _artifact_response(
        artifact.id,
        artifact.repository_id,
        artifact.path,
        artifact.name,
        artifact.checksum,
        artifact.size,
        _build_public_url(
            repository_id=artifact.repository_id,
            artifact_id=artifact.id,
            path=artifact.path,
            allow_public_object_urls=access.repository.allow_public_object_urls,
        ),
    )


@router.get("/{version_id}/artifacts", response_model=ArtifactListResponse)
async def list_version_artifacts(
    version_id: UUID,
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> ArtifactListResponse:
    version = await VersionReadValidator.validate(uow=uow, version_id=version_id)
    access = await RepositoryAccessValidator.validate(
        uow=uow,
        repository_id=version.repository_id,
        current_user=current_user,
    )
    await authorize(
        current_user,
        VersionPolicy.read,
        access,
        unauthorized_message="Missing bearer token",
        unauthorized_app_status=AppStatus.ERROR_MISSING_BEARER_TOKEN,
    )
    artifacts = await VersionArtifactService(uow).list_for_version(version)
    return ArtifactListResponse(
        items=[
            _artifact_response(
                artifact.id,
                artifact.repository_id,
                artifact.path,
                artifact.name,
                artifact.checksum,
                artifact.size,
                _build_public_url(
                    repository_id=artifact.repository_id,
                    artifact_id=artifact.id,
                    path=artifact.path,
                    allow_public_object_urls=access.repository.allow_public_object_urls,
                ),
            )
            for artifact in artifacts
        ]
    )


@router.delete("/{version_id}/artifacts", response_model=VersionArtifactClearResponse)
async def clear_version_artifacts(
    version_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> VersionArtifactClearResponse:
    version = await VersionReadValidator.validate(uow=uow, version_id=version_id)
    access = await RepositoryAccessValidator.validate(
        uow=uow,
        repository_id=version.repository_id,
        current_user=current_user,
    )
    await authorize(current_user, VersionPolicy.delete, access)
    deleted = await VersionArtifactService(uow).clear_for_version(version=version)
    return VersionArtifactClearResponse(deleted=deleted)


@router.delete("/{version_id}/artifacts/by-path", response_model=VersionArtifactClearResponse)
async def clear_version_artifact_by_path(
    version_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    request: VersionArtifactPathClearRequest | None = None,
    path: Annotated[str | None, Query()] = None,
) -> VersionArtifactClearResponse:
    version = await VersionReadValidator.validate(uow=uow, version_id=version_id)
    access = await RepositoryAccessValidator.validate(
        uow=uow,
        repository_id=version.repository_id,
        current_user=current_user,
    )
    await authorize(current_user, VersionPolicy.delete, access)
    normalized_path = path if path is not None else request.path if request is not None else ""
    await VersionArtifactPathReadValidator.validate(uow=uow, version=version, path=normalized_path)
    deleted = await VersionArtifactService(uow).clear_for_path(version=version, path=normalized_path)
    return VersionArtifactClearResponse(deleted=deleted)


@router.get("/{version_id}/artifacts/by-path", response_model=ArtifactResponse)
async def get_version_artifact_by_path(
    version_id: UUID,
    path: Annotated[str, Query()],
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> ArtifactResponse:
    version = await VersionReadValidator.validate(uow=uow, version_id=version_id)
    access = await RepositoryAccessValidator.validate(
        uow=uow,
        repository_id=version.repository_id,
        current_user=current_user,
    )
    await authorize(
        current_user,
        DownloadPolicy.read,
        access,
        unauthorized_message="Missing bearer token",
        unauthorized_app_status=AppStatus.ERROR_MISSING_BEARER_TOKEN,
    )
    artifact = await VersionArtifactPathReadValidator.validate(uow=uow, version=version, path=path)
    return _artifact_response(
        artifact.id,
        artifact.repository_id,
        artifact.path,
        artifact.name,
        artifact.checksum,
        artifact.size,
        _build_public_url(
            repository_id=artifact.repository_id,
            artifact_id=artifact.id,
            path=artifact.path,
            allow_public_object_urls=access.repository.allow_public_object_urls,
        ),
    )


@router.post("/{version_id}/artifacts/{artifact_id}/download", response_model=ArtifactDownloadResponse)
async def create_version_artifact_download(
    version_id: UUID,
    artifact_id: UUID,
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> ArtifactDownloadResponse:
    version = await VersionReadValidator.validate(uow=uow, version_id=version_id)
    access = await RepositoryAccessValidator.validate(
        uow=uow,
        repository_id=version.repository_id,
        current_user=current_user,
    )
    await authorize(
        current_user,
        DownloadPolicy.read,
        access,
        unauthorized_message="Missing bearer token",
        unauthorized_app_status=AppStatus.ERROR_MISSING_BEARER_TOKEN,
    )
    artifact = await VersionArtifactReadValidator.validate(uow=uow, version=version, artifact_id=artifact_id)
    download_url, expires_in = await DownloadService(uow).get_download_url(version_id=version_id, artifact=artifact)
    return ArtifactDownloadResponse(
        artifact_id=artifact_id,
        download_url=download_url,
        expires_in=expires_in,
    )
