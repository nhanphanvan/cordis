from cordis.sdk.errors import ApiError as SdkApiError
from cordis.sdk.errors import CordisError
from cordis.sdk.errors import TransportError as SdkTransportError


class CordisCliError(CordisError):
    """CLI-facing compatibility alias for shared Cordis errors."""


class ConfigurationError(CordisCliError):
    def __init__(self, user_message: str) -> None:
        super().__init__(user_message=user_message, status_line="CONFIG")


class TransportError(SdkTransportError, CordisCliError):
    """CLI transport error preserving legacy catch behavior."""


class ApiError(SdkApiError, CordisCliError):
    """CLI API error preserving legacy catch behavior."""
