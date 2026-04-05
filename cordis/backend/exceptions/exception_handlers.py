import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette import status

from cordis.backend.exceptions import exceptions
from cordis.backend.exceptions.app_status import AppStatus

logger = logging.getLogger(__name__)


def _build_error_response(exc: exceptions.CordisException) -> dict[str, Any]:
    response: dict[str, Any] = {
        "status_code": exc.app_status.status_code,
        "app_status_code": exc.app_status.app_status_code,
        "message": exc.app_status.message,
        "detail": str(exc),
    }
    if exc.extra:
        response.update(exc.extra)
    return response


def _log_handled_exception(request: Request, exc: exceptions.CordisException) -> None:
    logger.error(
        "Cordis exception handled path=%s status=%s app_status=%s detail=%s",
        request.url.path,
        exc.app_status.status_code,
        exc.app_status.app_status_code,
        str(exc),
    )


def _custom_external_service_error_handler(request: Request, exc: exceptions.ExternalServiceError) -> JSONResponse:
    _log_handled_exception(request, exc)
    return JSONResponse(status_code=exc.app_status.status_code, content=_build_error_response(exc))


def _custom_not_found_error_handler(request: Request, exc: exceptions.NotFoundError) -> JSONResponse:
    _log_handled_exception(request, exc)
    return JSONResponse(status_code=exc.app_status.status_code, content=_build_error_response(exc))


def _custom_unprocessable_entity_error_handler(
    request: Request,
    exc: exceptions.UnprocessableEntityError,
) -> JSONResponse:
    _log_handled_exception(request, exc)
    return JSONResponse(status_code=exc.app_status.status_code, content=_build_error_response(exc))


def _custom_conflict_error_handler(request: Request, exc: exceptions.ConflictError) -> JSONResponse:
    _log_handled_exception(request, exc)
    return JSONResponse(status_code=exc.app_status.status_code, content=_build_error_response(exc))


def _custom_not_unique_error_handler(request: Request, exc: exceptions.NotUniqueError) -> JSONResponse:
    _log_handled_exception(request, exc)
    return JSONResponse(status_code=exc.app_status.status_code, content=_build_error_response(exc))


def _custom_forbidden_operation_error_handler(
    request: Request,
    exc: exceptions.ForbiddenOperationError,
) -> JSONResponse:
    _log_handled_exception(request, exc)
    return JSONResponse(status_code=exc.app_status.status_code, content=_build_error_response(exc))


def _custom_internal_server_error_handler(request: Request, exc: exceptions.InternalServerError) -> JSONResponse:
    _log_handled_exception(request, exc)
    return JSONResponse(status_code=exc.app_status.status_code, content=_build_error_response(exc))


def _custom_unauthorized_error_handler(request: Request, exc: exceptions.UnauthorizedError) -> JSONResponse:
    _log_handled_exception(request, exc)
    return JSONResponse(status_code=exc.app_status.status_code, content=_build_error_response(exc))


def _custom_bad_request_error_handler(request: Request, exc: exceptions.BadRequestError) -> JSONResponse:
    _log_handled_exception(request, exc)
    return JSONResponse(status_code=exc.app_status.status_code, content=_build_error_response(exc))


def _custom_request_validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    logger.warning("Request validation failed detail=%s", exc.errors())
    return JSONResponse(
        status_code=AppStatus.ERROR_VALIDATION.status_code,
        content={
            "status_code": AppStatus.ERROR_VALIDATION.status_code,
            "app_status_code": AppStatus.ERROR_VALIDATION.app_status_code,
            "message": AppStatus.ERROR_VALIDATION.message,
            "detail": exc.errors(),
        },
    )


def _custom_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception path=%s detail=%s", request.url.path, str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "app_status_code": AppStatus.ERROR_INTERNAL_SERVER_ERROR.app_status_code,
            "message": AppStatus.ERROR_INTERNAL_SERVER_ERROR.message,
            "detail": str(exc),
        },
    )


def configure_exception_handlers(app: FastAPI) -> None:
    app.exception_handler(exceptions.ExternalServiceError)(_custom_external_service_error_handler)
    app.exception_handler(exceptions.NotFoundError)(_custom_not_found_error_handler)
    app.exception_handler(exceptions.UnprocessableEntityError)(_custom_unprocessable_entity_error_handler)
    app.exception_handler(exceptions.ConflictError)(_custom_conflict_error_handler)
    app.exception_handler(exceptions.NotUniqueError)(_custom_not_unique_error_handler)
    app.exception_handler(exceptions.ForbiddenOperationError)(_custom_forbidden_operation_error_handler)
    app.exception_handler(exceptions.InternalServerError)(_custom_internal_server_error_handler)
    app.exception_handler(exceptions.UnauthorizedError)(_custom_unauthorized_error_handler)
    app.exception_handler(exceptions.BadRequestError)(_custom_bad_request_error_handler)
    app.exception_handler(RequestValidationError)(_custom_request_validation_error_handler)
    app.exception_handler(Exception)(_custom_exception_handler)
