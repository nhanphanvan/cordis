from functools import lru_cache

from cordis.backend.storage.protocol import StorageAdapter
from cordis.shared.errors import InfrastructureError


@lru_cache(maxsize=1)
def get_storage_adapter() -> StorageAdapter:
    raise InfrastructureError("Storage adapter is not configured")
