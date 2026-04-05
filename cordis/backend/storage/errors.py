from cordis.backend.exceptions import AppStatus, ConflictError, ExternalServiceError, NotFoundError


class StorageObjectNotFoundError(NotFoundError):
    def __init__(self, message: str = "Storage object not found") -> None:
        super().__init__(message=message, app_status=AppStatus.ERROR_STORAGE_OBJECT_NOT_FOUND)


class StorageConflictError(ConflictError):
    def __init__(self, message: str = "Storage object conflict") -> None:
        super().__init__(message=message, app_status=AppStatus.ERROR_STORAGE_CONFLICT)


class StorageMultipartStateError(ConflictError):
    def __init__(self, message: str = "Storage multipart state invalid") -> None:
        super().__init__(message=message, app_status=AppStatus.ERROR_STORAGE_MULTIPART_STATE_INVALID)


class StorageAuthorizationError(ExternalServiceError):
    def __init__(self, message: str = "Storage provider authorization failed") -> None:
        super().__init__(message=message, app_status=AppStatus.ERROR_STORAGE_PROVIDER_AUTHORIZATION)


class StorageTransientError(ExternalServiceError):
    def __init__(self, message: str = "Transient storage provider failure") -> None:
        super().__init__(message=message, app_status=AppStatus.ERROR_STORAGE_PROVIDER_TRANSIENT)


class StorageProviderError(ExternalServiceError):
    def __init__(self, message: str = "Unrecoverable storage provider failure") -> None:
        super().__init__(message=message, app_status=AppStatus.ERROR_STORAGE_PROVIDER_FAILURE)
