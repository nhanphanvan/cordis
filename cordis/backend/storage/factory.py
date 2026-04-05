from functools import lru_cache

from cordis.backend.exceptions import AppStatus, InternalServerError
from cordis.backend.storage.protocol import StorageAdapter


@lru_cache(maxsize=1)
def get_storage_adapter() -> StorageAdapter:
    raise InternalServerError(
        "Storage adapter is not configured",
        app_status=AppStatus.ERROR_STORAGE_ADAPTER_NOT_CONFIGURED,
    )
