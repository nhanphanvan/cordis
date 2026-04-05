from functools import lru_cache

from cordis.backend.errors import InfrastructureError
from cordis.backend.storage.protocol import StorageAdapter


@lru_cache(maxsize=1)
def get_storage_adapter() -> StorageAdapter:
    raise InfrastructureError("Storage adapter is not configured")
