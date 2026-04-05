from dataclasses import dataclass


@dataclass(slots=True)
class CordisError(Exception):
    code: str
    message: str
    status_code: int


class ValidationError(CordisError):
    def __init__(self, message: str = "Validation failed") -> None:
        super().__init__(code="validation_error", message=message, status_code=422)


class AuthenticationError(CordisError):
    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(code="authentication_error", message=message, status_code=401)


class AuthorizationError(CordisError):
    def __init__(self, message: str = "Not enough privileges") -> None:
        super().__init__(code="authorization_error", message=message, status_code=403)


class NotFoundError(CordisError):
    def __init__(self, message: str = "Entity not found") -> None:
        super().__init__(code="not_found", message=message, status_code=404)


class ConflictError(CordisError):
    def __init__(self, message: str = "Conflict detected") -> None:
        super().__init__(code="conflict", message=message, status_code=409)


class InfrastructureError(CordisError):
    def __init__(self, message: str = "Infrastructure failure") -> None:
        super().__init__(code="infrastructure_error", message=message, status_code=500)
