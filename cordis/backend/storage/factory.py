from functools import lru_cache
from typing import cast

from minio import Minio

from cordis.backend.config import build_config
from cordis.backend.exceptions import AppStatus, InternalServerError
from cordis.backend.storage.minio import MinioStorageClient
from cordis.backend.storage.protocol import StorageAdapter
from cordis.backend.storage.s3 import S3StorageAdapter


@lru_cache(maxsize=1)
def get_storage_adapter() -> StorageAdapter:
    config = build_config().storage
    if config.provider != "minio":
        raise InternalServerError(
            f"Storage provider '{config.provider}' is not configured",
            app_status=AppStatus.ERROR_STORAGE_ADAPTER_NOT_CONFIGURED,
        )

    missing_fields = [
        field_name
        for field_name, value in (
            ("CORDIS_STORAGE_ENDPOINT", config.endpoint),
            ("CORDIS_STORAGE_ACCESS_KEY", config.access_key),
            ("CORDIS_STORAGE_SECRET_KEY", config.secret_key),
        )
        if not value
    ]
    if missing_fields:
        raise InternalServerError(
            "Storage adapter is not configured: missing " + ", ".join(missing_fields),
            app_status=AppStatus.ERROR_STORAGE_ADAPTER_NOT_CONFIGURED,
        )

    endpoint = cast(str, config.endpoint)
    access_key = cast(str, config.access_key)
    secret_key = cast(str, config.secret_key)

    client = MinioStorageClient(
        Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=config.secure,
            region=config.region,
        )
    )
    client.ensure_bucket_exists(bucket=config.bucket, region=config.region)
    client.ensure_bucket_versioning_enabled(bucket=config.bucket)
    return S3StorageAdapter(client=client, bucket=config.bucket, prefix=config.prefix)
