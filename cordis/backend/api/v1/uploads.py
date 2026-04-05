import base64
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from cordis.backend.api.dependencies import get_current_user, get_uow
from cordis.backend.models import UploadSession, UploadSessionPart, User
from cordis.backend.policies import UploadPolicy, authorize
from cordis.backend.repositories.unit_of_work import UnitOfWork
from cordis.backend.schemas.requests.upload import (
    UploadSessionCreateRequest,
    UploadSessionPartCreateRequest,
)
from cordis.backend.schemas.responses.upload import (
    UploadSessionPartResponse,
    UploadSessionResponse,
)
from cordis.backend.services.upload import UploadService
from cordis.backend.validators.repository import RepositoryAccessValidator
from cordis.backend.validators.upload import (
    UploadSessionCompletionValidator,
    UploadSessionCreateValidator,
    UploadSessionMutableValidator,
    UploadSessionReadValidator,
)
from cordis.backend.validators.version import VersionReadValidator

router = APIRouter(prefix="/uploads/sessions", tags=["uploads"])


def _session_response(session: UploadSession, parts: list[UploadSessionPart]) -> UploadSessionResponse:
    artifact_id = session.artifact_id if session.status == "completed" else None
    return UploadSessionResponse(
        id=session.id,
        repository_id=session.repository_id,
        version_id=session.version_id,
        artifact_id=artifact_id,
        path=session.path,
        checksum=session.checksum,
        size=session.size,
        upload_id=session.upload_id,
        status=session.status,
        error_message=session.error_message,
        parts=[UploadSessionPartResponse(part_number=part.part_number, etag=part.etag) for part in parts],
    )


@router.post("", response_model=UploadSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_upload_session(
    request: UploadSessionCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    response: Response,
) -> UploadSessionResponse:
    upload_input = await UploadSessionCreateValidator.validate(uow=uow, request=request)
    access = await RepositoryAccessValidator.validate(
        uow=uow,
        repository_id=upload_input.version.repository_id,
        current_user=current_user,
    )
    await authorize(current_user, UploadPolicy.mutate, access)
    session, created = await UploadService(uow).create_or_resume_session(
        version=upload_input.version,
        path=upload_input.normalized_path,
        checksum=upload_input.checksum,
        size=upload_input.size,
    )
    parts = await uow.upload_session_parts.list_for_session(session.id)
    payload = _session_response(session, parts)
    if not created:
        response.status_code = status.HTTP_200_OK
    return payload


@router.get("/{session_id}", response_model=UploadSessionResponse)
async def get_upload_session(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> UploadSessionResponse:
    session, parts = await UploadSessionReadValidator.validate(uow=uow, session_id=session_id)
    access = await RepositoryAccessValidator.validate(
        uow=uow,
        repository_id=session.repository_id,
        current_user=current_user,
    )
    await authorize(current_user, UploadPolicy.mutate, access)
    return _session_response(session, parts)


@router.post("/{session_id}/parts", response_model=UploadSessionResponse)
async def upload_session_part(
    session_id: str,
    request: UploadSessionPartCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> UploadSessionResponse:
    session, _ = await UploadSessionReadValidator.validate(uow=uow, session_id=session_id)
    access = await RepositoryAccessValidator.validate(
        uow=uow,
        repository_id=session.repository_id,
        current_user=current_user,
    )
    await authorize(current_user, UploadPolicy.mutate, access)
    await UploadSessionMutableValidator.validate(session=session)
    if request.content_base64 is not None:
        content_bytes = base64.b64decode(request.content_base64.encode("ascii"))
    elif request.content is not None:
        content_bytes = request.content.encode()
    else:
        content_bytes = b""
    updated_session, parts = await UploadService(uow).upload_part(
        session=session,
        part_number=request.part_number,
        content_bytes=content_bytes,
    )
    return _session_response(updated_session, parts)


@router.post("/{session_id}/complete", response_model=UploadSessionResponse)
async def complete_upload_session(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> UploadSessionResponse:
    session, parts = await UploadSessionReadValidator.validate(uow=uow, session_id=session_id)
    version = await VersionReadValidator.validate(uow=uow, version_id=session.version_id)
    access = await RepositoryAccessValidator.validate(
        uow=uow,
        repository_id=session.repository_id,
        current_user=current_user,
    )
    await authorize(current_user, UploadPolicy.mutate, access)
    session, parts = await UploadSessionCompletionValidator.validate(session=session, parts=parts)
    updated_session, parts = await UploadService(uow).complete_session(
        session=session,
        parts=parts,
        version=version,
        repository=access.repository,
    )
    return _session_response(updated_session, parts)


@router.post("/{session_id}/abort", response_model=UploadSessionResponse)
async def abort_upload_session(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> UploadSessionResponse:
    session, _ = await UploadSessionReadValidator.validate(uow=uow, session_id=session_id)
    access = await RepositoryAccessValidator.validate(
        uow=uow,
        repository_id=session.repository_id,
        current_user=current_user,
    )
    await authorize(current_user, UploadPolicy.mutate, access)
    updated_session, parts = await UploadService(uow).abort_session(session)
    return _session_response(updated_session, parts)
