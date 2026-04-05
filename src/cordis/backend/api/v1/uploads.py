import base64
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from cordis.backend.api.dependencies import get_current_user, get_uow
from cordis.backend.models import UploadSession, UploadSessionPart, User
from cordis.backend.repositories.unit_of_work import UnitOfWork
from cordis.backend.schemas.upload import (
    UploadSessionCreateRequest,
    UploadSessionPartCreateRequest,
    UploadSessionPartResponse,
    UploadSessionResponse,
)
from cordis.backend.services.authorization import AuthorizationService
from cordis.backend.services.upload import UploadService
from cordis.backend.services.version import VersionService

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
    version = await VersionService(uow).get_version(request.version_id)
    await AuthorizationService(uow).require_repository_access(
        repository_id=version.repository_id,
        required_role="developer",
        current_user=current_user,
    )
    session, created = await UploadService(uow).create_or_resume_session(
        version_id=request.version_id,
        path=request.path,
        checksum=request.checksum,
        size=request.size,
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
    session, parts = await UploadService(uow).get_session(session_id)
    await AuthorizationService(uow).require_repository_access(
        repository_id=session.repository_id,
        required_role="developer",
        current_user=current_user,
    )
    return _session_response(session, parts)


@router.post("/{session_id}/parts", response_model=UploadSessionResponse)
async def upload_session_part(
    session_id: str,
    request: UploadSessionPartCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> UploadSessionResponse:
    session, _ = await UploadService(uow).get_session(session_id)
    await AuthorizationService(uow).require_repository_access(
        repository_id=session.repository_id,
        required_role="developer",
        current_user=current_user,
    )
    if request.content_base64 is not None:
        content_bytes = base64.b64decode(request.content_base64.encode("ascii"))
    elif request.content is not None:
        content_bytes = request.content.encode()
    else:
        content_bytes = b""
    updated_session, parts = await UploadService(uow).upload_part(
        session_id=session_id,
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
    session, _ = await UploadService(uow).get_session(session_id)
    await AuthorizationService(uow).require_repository_access(
        repository_id=session.repository_id,
        required_role="developer",
        current_user=current_user,
    )
    updated_session, parts = await UploadService(uow).complete_session(session_id)
    return _session_response(updated_session, parts)


@router.post("/{session_id}/abort", response_model=UploadSessionResponse)
async def abort_upload_session(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> UploadSessionResponse:
    session, _ = await UploadService(uow).get_session(session_id)
    await AuthorizationService(uow).require_repository_access(
        repository_id=session.repository_id,
        required_role="developer",
        current_user=current_user,
    )
    updated_session, parts = await UploadService(uow).abort_session(session_id)
    return _session_response(updated_session, parts)
