from typing import Any

from botocore.client import BaseClient

S3_VERSIONING_ENABLED = "Enabled"


class AwsS3StorageClient:
    def __init__(self, client: BaseClient):
        self.client = client

    def bucket_exists(self, *, bucket: str) -> bool:
        self.client.head_bucket(Bucket=bucket)
        return True

    def bucket_versioning_enabled(self, *, bucket: str) -> bool:
        response = self.client.get_bucket_versioning(Bucket=bucket)
        return bool(response.get("Status") == S3_VERSIONING_ENABLED)

    def head_object(self, *, bucket: str, key: str) -> dict[str, Any]:
        response = self.client.head_object(Bucket=bucket, Key=key)
        return {
            "etag": str(response["ETag"]).strip('"'),
            "content_length": int(response["ContentLength"]),
        }

    def put_object(self, *, bucket: str, key: str, body: bytes, checksum: str | None) -> dict[str, Any]:
        checksum_sha256 = None if checksum is None else checksum.removeprefix("sha256:")
        response = self.client.put_object(Bucket=bucket, Key=key, Body=body, ChecksumSHA256=checksum_sha256)
        return {
            "etag": str(response["ETag"]).strip('"'),
            "version_id": None if response.get("VersionId") is None else str(response["VersionId"]),
        }

    def delete_object(self, *, bucket: str, key: str) -> None:
        self.client.delete_object(Bucket=bucket, Key=key)

    def create_presigned_get_url(self, *, bucket: str, key: str, expires_in: int) -> str:
        return str(
            self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=expires_in,
            )
        )

    def create_multipart_upload(self, *, bucket: str, key: str) -> dict[str, Any]:
        response = self.client.create_multipart_upload(Bucket=bucket, Key=key)
        return {"upload_id": str(response["UploadId"])}

    def upload_part(
        self,
        *,
        bucket: str,
        key: str,
        upload_id: str,
        part_number: int,
        body: bytes,
    ) -> dict[str, Any]:
        response = self.client.upload_part(
            Bucket=bucket,
            Key=key,
            UploadId=upload_id,
            PartNumber=part_number,
            Body=body,
        )
        return {"etag": str(response["ETag"]).strip('"')}

    def complete_multipart_upload(
        self,
        *,
        bucket: str,
        key: str,
        upload_id: str,
        parts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        response = self.client.complete_multipart_upload(
            Bucket=bucket,
            Key=key,
            UploadId=upload_id,
            MultipartUpload={"Parts": [{"PartNumber": part["part_number"], "ETag": part["etag"]} for part in parts]},
        )
        return {
            "etag": str(response["ETag"]).strip('"'),
            "version_id": None if response.get("VersionId") is None else str(response["VersionId"]),
        }

    def abort_multipart_upload(self, *, bucket: str, key: str, upload_id: str) -> None:
        self.client.abort_multipart_upload(Bucket=bucket, Key=key, UploadId=upload_id)
