from enum import Enum


class UploadSessionStatus(str, Enum):
    CREATED = "created"
    IN_PROGRESS = "in_progress"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


class ResourceCheckStatus(str, Enum):
    MISSING = "missing"
    EXISTS = "exists"
    CONFLICT = "conflict"


class RepositoryVisibility(str, Enum):
    PRIVATE = "private"
    AUTHENTICATED = "authenticated"


class RepositoryAccessRole(str, Enum):
    VIEWER = "viewer"
    DEVELOPER = "developer"
    OWNER = "owner"
