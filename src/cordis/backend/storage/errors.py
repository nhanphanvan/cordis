from cordis.shared.errors import CordisError


class StorageObjectNotFoundError(CordisError):
    def __init__(self, message: str = "Storage object not found") -> None:
        super().__init__(code="storage_object_not_found", message=message, status_code=404)


class StorageConflictError(CordisError):
    def __init__(self, message: str = "Storage object conflict") -> None:
        super().__init__(code="storage_conflict", message=message, status_code=409)


class StorageMultipartStateError(CordisError):
    def __init__(self, message: str = "Storage multipart state invalid") -> None:
        super().__init__(code="storage_multipart_state_error", message=message, status_code=409)


class StorageAuthorizationError(CordisError):
    def __init__(self, message: str = "Storage provider authorization failed") -> None:
        super().__init__(code="storage_authorization_error", message=message, status_code=502)


class StorageTransientError(CordisError):
    def __init__(self, message: str = "Transient storage provider failure") -> None:
        super().__init__(code="storage_transient_error", message=message, status_code=503)


class StorageProviderError(CordisError):
    def __init__(self, message: str = "Unrecoverable storage provider failure") -> None:
        super().__init__(code="storage_provider_error", message=message, status_code=502)
