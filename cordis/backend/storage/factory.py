from functools import lru_cache
from typing import cast

import boto3
from minio import Minio

from cordis.backend.config import build_config
from cordis.backend.exceptions import AppStatus, InternalServerError
from cordis.backend.storage.aws import AwsS3StorageClient
from cordis.backend.storage.minio import MinioStorageClient
from cordis.backend.storage.protocol import StorageAdapter
from cordis.backend.storage.s3 import S3StorageAdapter


@lru_cache(maxsize=1)
def get_storage_adapter() -> StorageAdapter:
    config = build_config().storage
    if config.provider == "minio":
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

        minio_client = MinioStorageClient(
            Minio(
                endpoint,
                access_key=access_key,
                secret_key=secret_key,
                secure=config.secure,
                region=config.region,
            )
        )
        minio_client.ensure_bucket_exists(bucket=config.bucket, region=config.region)
        minio_client.ensure_bucket_versioning_enabled(bucket=config.bucket)
        return S3StorageAdapter(client=minio_client, bucket=config.bucket, prefix=config.prefix)

    if config.provider == "s3":
        boto_kwargs: dict[str, object] = {}
        if config.region:
            boto_kwargs["region_name"] = config.region
        if config.endpoint:
            boto_kwargs["endpoint_url"] = config.endpoint
        if config.access_key:
            boto_kwargs["aws_access_key_id"] = config.access_key
        if config.secret_key:
            boto_kwargs["aws_secret_access_key"] = config.secret_key

        aws_client = AwsS3StorageClient(boto3.client("s3", **boto_kwargs))
        try:
            aws_client.bucket_exists(bucket=config.bucket)
        except Exception as error:
            raise InternalServerError(
                "Storage adapter is not configured: S3 bucket is missing or inaccessible",
                app_status=AppStatus.ERROR_STORAGE_ADAPTER_NOT_CONFIGURED,
            ) from error

        if not aws_client.bucket_versioning_enabled(bucket=config.bucket):
            raise InternalServerError(
                "Storage adapter is not configured: S3 bucket versioning must be enabled",
                app_status=AppStatus.ERROR_STORAGE_ADAPTER_NOT_CONFIGURED,
            )
        return S3StorageAdapter(client=aws_client, bucket=config.bucket, prefix=config.prefix)

    raise InternalServerError(
        f"Storage provider '{config.provider}' is not configured",
        app_status=AppStatus.ERROR_STORAGE_ADAPTER_NOT_CONFIGURED,
    )
