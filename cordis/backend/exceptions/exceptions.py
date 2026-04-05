from typing import Any

from cordis.backend.exceptions.app_status import AppStatus


class CordisException(Exception):
    def __init__(
        self,
        message: str | None = None,
        *,
        app_status: AppStatus = AppStatus.ERROR_INTERNAL_SERVER_ERROR,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.app_status = app_status
        self.custom_message = message
        self.extra = extra or {}
        super().__init__(message or app_status.message)

    def __str__(self) -> str:
        return self.custom_message or self.app_status.message


class ExternalServiceError(CordisException):
    def __init__(
        self,
        message: str | None = None,
        *,
        app_status: AppStatus = AppStatus.ERROR_SERVICE_UNAVAILABLE,
        extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, app_status=app_status, extra=extra)


class NotFoundError(CordisException):
    def __init__(
        self,
        message: str | None = None,
        *,
        app_status: AppStatus = AppStatus.ERROR_NOT_FOUND,
        extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, app_status=app_status, extra=extra)


class UnprocessableEntityError(CordisException):
    def __init__(
        self,
        message: str | None = None,
        *,
        app_status: AppStatus = AppStatus.ERROR_UNPROCESSABLE_ENTITY,
        extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, app_status=app_status, extra=extra)


class ConflictError(CordisException):
    def __init__(
        self,
        message: str | None = None,
        *,
        app_status: AppStatus = AppStatus.ERROR_CONFLICT,
        extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, app_status=app_status, extra=extra)


class NotUniqueError(ConflictError):
    pass


class ForbiddenOperationError(CordisException):
    def __init__(
        self,
        message: str | None = None,
        *,
        app_status: AppStatus = AppStatus.ERROR_FORBIDDEN,
        extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, app_status=app_status, extra=extra)


class InternalServerError(CordisException):
    def __init__(
        self,
        message: str | None = None,
        *,
        app_status: AppStatus = AppStatus.ERROR_INTERNAL_SERVER_ERROR,
        extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, app_status=app_status, extra=extra)


class UnauthorizedError(CordisException):
    def __init__(
        self,
        message: str | None = None,
        *,
        app_status: AppStatus = AppStatus.ERROR_UNAUTHORIZED,
        extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, app_status=app_status, extra=extra)


class BadRequestError(CordisException):
    def __init__(
        self,
        message: str | None = None,
        *,
        app_status: AppStatus = AppStatus.ERROR_BAD_REQUEST,
        extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, app_status=app_status, extra=extra)
