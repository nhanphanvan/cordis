class CordisError(Exception):
    def __init__(self, *, user_message: str, status_line: str) -> None:
        super().__init__(user_message)
        self.user_message = user_message
        self.status_line = status_line


class TransportError(CordisError):
    def __init__(self, user_message: str, detail: str | None = None) -> None:
        super().__init__(user_message=user_message, status_line="TRANSPORT")
        self.detail = detail


class ApiError(CordisError):
    def __init__(
        self,
        *,
        http_status: int,
        app_status_code: int | None,
        status_message: str,
        user_message: str,
        detail: str | None = None,
    ) -> None:
        status_line = f"HTTP {http_status}"
        if app_status_code is not None:
            status_line = f"{status_line} • APP {app_status_code}"
        super().__init__(user_message=user_message, status_line=status_line)
        self.http_status = http_status
        self.app_status_code = app_status_code
        self.status_message = status_message
        self.detail = detail


class UploadPreflightError(CordisError):
    def __init__(self, *, conflicts: list[str]) -> None:
        conflict_lines = "\n".join(conflicts)
        super().__init__(
            user_message=(f"Upload preflight failed. No files were uploaded.\n\nConflicting paths:\n{conflict_lines}"),
            status_line="UPLOAD PREFLIGHT",
        )
        self.conflicts = conflicts
