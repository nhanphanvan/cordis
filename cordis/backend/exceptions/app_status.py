from enum import Enum
from typing import Any

from starlette import status

HTTP_422_UNPROCESSABLE = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)


class AppStatus(Enum):
    """Application status catalog for API error responses.

    Code ranges:
    - `4xx` and `5xx`: generic HTTP-aligned fallback statuses
    - `1000-1099`: authentication, bearer token, and general validation errors
    - `1100-1199`: repository and repository membership errors
    - `1200-1299`: role errors
    - `1300-1399`: user errors
    - `1400-1499`: version errors
    - `1500-1599`: tag errors
    - `1600-1699`: artifact and version-artifact errors
    - `1700-1799`: upload session and upload validation errors
    - `1800-1899`: storage provider and object-state errors
    - `1900-1999`: backend configuration and invariant errors
    """

    ERROR_INTERNAL_SERVER_ERROR = status.HTTP_500_INTERNAL_SERVER_ERROR, 500, "Internal server error"
    ERROR_NOT_FOUND = status.HTTP_404_NOT_FOUND, 404, "Resource not found"
    ERROR_BAD_REQUEST = status.HTTP_400_BAD_REQUEST, 400, "Bad request"
    ERROR_UNAUTHORIZED = status.HTTP_401_UNAUTHORIZED, 401, "Unauthorized"
    ERROR_FORBIDDEN = status.HTTP_403_FORBIDDEN, 403, "Forbidden"
    ERROR_CONFLICT = status.HTTP_409_CONFLICT, 409, "Conflict"
    ERROR_UNPROCESSABLE_ENTITY = HTTP_422_UNPROCESSABLE, 422, "Unprocessable entity"
    ERROR_SERVICE_UNAVAILABLE = status.HTTP_503_SERVICE_UNAVAILABLE, 503, "Service unavailable"

    ERROR_VALIDATION = HTTP_422_UNPROCESSABLE, 1000, "Validation error"
    ERROR_INVALID_CREDENTIALS = status.HTTP_401_UNAUTHORIZED, 1001, "Invalid credentials"
    ERROR_INVALID_BEARER_TOKEN = status.HTTP_401_UNAUTHORIZED, 1002, "Invalid bearer token"
    ERROR_EXPIRED_BEARER_TOKEN = status.HTTP_401_UNAUTHORIZED, 1003, "Expired bearer token"
    ERROR_MISSING_BEARER_TOKEN = status.HTTP_401_UNAUTHORIZED, 1004, "Missing bearer token"
    ERROR_ADMIN_PRIVILEGES_REQUIRED = status.HTTP_403_FORBIDDEN, 1005, "Admin privileges required"
    ERROR_REPOSITORY_ACCESS_DENIED = status.HTTP_403_FORBIDDEN, 1006, "Repository access denied"

    ERROR_REPOSITORY_NOT_FOUND = status.HTTP_404_NOT_FOUND, 1100, "Repository not found"
    ERROR_REPOSITORY_NAME_ALREADY_EXISTS = status.HTTP_409_CONFLICT, 1101, "Repository name already exists"
    ERROR_REPOSITORY_MEMBER_ALREADY_EXISTS = status.HTTP_409_CONFLICT, 1102, "Repository member already exists"
    ERROR_REPOSITORY_MEMBER_NOT_FOUND = status.HTTP_404_NOT_FOUND, 1103, "Repository member not found"
    ERROR_REPOSITORY_ROLE_INVALID = HTTP_422_UNPROCESSABLE, 1104, "Invalid repository role"

    ERROR_ROLE_NOT_FOUND = status.HTTP_404_NOT_FOUND, 1200, "Role not found"
    ERROR_ROLE_NAME_ALREADY_EXISTS = status.HTTP_409_CONFLICT, 1201, "Role name already exists"

    ERROR_USER_NOT_FOUND = status.HTTP_404_NOT_FOUND, 1300, "User not found"
    ERROR_USER_EMAIL_ALREADY_EXISTS = status.HTTP_409_CONFLICT, 1301, "User email already exists"

    ERROR_VERSION_NOT_FOUND = status.HTTP_404_NOT_FOUND, 1400, "Version not found"
    ERROR_VERSION_NAME_ALREADY_EXISTS = status.HTTP_409_CONFLICT, 1401, "Version name already exists in repository"

    ERROR_TAG_NOT_FOUND = status.HTTP_404_NOT_FOUND, 1500, "Tag not found"
    ERROR_TAG_NAME_ALREADY_EXISTS = status.HTTP_409_CONFLICT, 1501, "Tag name already exists in repository"
    ERROR_TAG_VERSION_REPOSITORY_MISMATCH = (
        HTTP_422_UNPROCESSABLE,
        1502,
        "Version does not belong to repository",
    )

    ERROR_ARTIFACT_NOT_FOUND = status.HTTP_404_NOT_FOUND, 1600, "Artifact not found"
    ERROR_ARTIFACT_PATH_ALREADY_EXISTS = status.HTTP_409_CONFLICT, 1601, "Artifact path already exists in repository"
    ERROR_ARTIFACT_PATH_INVALID = HTTP_422_UNPROCESSABLE, 1602, "Artifact path is invalid"
    ERROR_ARTIFACT_CHECKSUM_CONFLICT = (
        status.HTTP_409_CONFLICT,
        1603,
        "Artifact path already exists in repository with different metadata",
    )
    ERROR_ARTIFACT_REPOSITORY_MISMATCH = (
        HTTP_422_UNPROCESSABLE,
        1604,
        "Artifact does not belong to version repository",
    )
    ERROR_ARTIFACT_VERSION_PATH_CONFLICT = status.HTTP_409_CONFLICT, 1605, "Artifact path already exists in version"
    ERROR_ARTIFACT_ALREADY_EXISTS_IN_VERSION = status.HTTP_409_CONFLICT, 1606, "Artifact already exists in version"
    ERROR_ARTIFACT_VERSION_METADATA_CONFLICT = (
        status.HTTP_409_CONFLICT,
        1607,
        "Artifact path already exists in version with different metadata",
    )

    ERROR_UPLOAD_SESSION_NOT_FOUND = status.HTTP_404_NOT_FOUND, 1700, "Upload session not found"
    ERROR_UPLOAD_SESSION_TERMINAL = status.HTTP_409_CONFLICT, 1701, "Upload session is already terminal"
    ERROR_UPLOAD_SESSION_NO_PARTS = HTTP_422_UNPROCESSABLE, 1702, "Upload session has no uploaded parts"
    ERROR_UPLOAD_CHECKSUM_MISMATCH = (
        status.HTTP_409_CONFLICT,
        1703,
        "Completed upload checksum does not match expected checksum",
    )
    ERROR_UPLOAD_SIZE_INVALID = HTTP_422_UNPROCESSABLE, 1704, "Upload size must be non-negative"
    ERROR_UPLOAD_PATH_INVALID = HTTP_422_UNPROCESSABLE, 1705, "Upload path must not be empty"

    ERROR_STORAGE_OBJECT_NOT_FOUND = status.HTTP_404_NOT_FOUND, 1800, "Storage object not found"
    ERROR_STORAGE_CONFLICT = status.HTTP_409_CONFLICT, 1801, "Storage object conflict"
    ERROR_STORAGE_MULTIPART_STATE_INVALID = status.HTTP_409_CONFLICT, 1802, "Storage multipart state invalid"
    ERROR_STORAGE_PROVIDER_AUTHORIZATION = (
        status.HTTP_502_BAD_GATEWAY,
        1803,
        "Storage provider authorization failed",
    )
    ERROR_STORAGE_PROVIDER_TRANSIENT = status.HTTP_503_SERVICE_UNAVAILABLE, 1804, "Transient storage provider failure"
    ERROR_STORAGE_PROVIDER_FAILURE = (
        status.HTTP_502_BAD_GATEWAY,
        1805,
        "Unrecoverable storage provider failure",
    )

    ERROR_STORAGE_ADAPTER_NOT_CONFIGURED = (
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        1900,
        "Storage adapter is not configured",
    )
    ERROR_OWNER_ROLE_MISSING = status.HTTP_500_INTERNAL_SERVER_ERROR, 1901, "Owner role is missing"
    ERROR_STORAGE_VERSION_ID_MISSING = status.HTTP_500_INTERNAL_SERVER_ERROR, 1902, "Storage version ID missing"

    @property
    def status_code(self) -> int:
        return self.value[0]

    @property
    def app_status_code(self) -> int:
        return self.value[1]

    @property
    def message(self) -> str:
        return self.value[2]

    @property
    def meta(self) -> dict[str, Any]:
        return {"status_code": self.status_code, "app_status_code": self.app_status_code, "message": self.message}
