from cordis.backend.enums import RepositoryAccessRole, UploadSessionStatus

BUILTIN_OWNER_ROLE = RepositoryAccessRole.OWNER

ROLE_RANK = {
    RepositoryAccessRole.VIEWER: 1,
    RepositoryAccessRole.DEVELOPER: 2,
    RepositoryAccessRole.OWNER: 3,
}

ROLE_RANK_BY_NAME = {role.value: rank for role, rank in ROLE_RANK.items()}

UPLOAD_TERMINAL_STATUSES = frozenset(
    {
        UploadSessionStatus.COMPLETED,
        UploadSessionStatus.FAILED,
        UploadSessionStatus.ABORTED,
    }
)

UPLOAD_RESUMABLE_STATUSES = frozenset(
    {
        UploadSessionStatus.CREATED,
        UploadSessionStatus.IN_PROGRESS,
        UploadSessionStatus.FINALIZING,
    }
)
