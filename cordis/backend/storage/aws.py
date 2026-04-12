import json
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

    def create_public_object_url(self, *, bucket: str, key: str, version_id: str) -> str:
        meta = getattr(self.client, "meta", None)
        endpoint_url = getattr(meta, "endpoint_url", None)
        if isinstance(endpoint_url, str):
            host = endpoint_url.rstrip("/")
            return f"{host}/{bucket}/{key}?versionId={version_id}"

        region_name = getattr(getattr(meta, "config", None), "region_name", None)
        if region_name:
            return f"https://{bucket}.s3.{region_name}.amazonaws.com/{key}?versionId={version_id}"
        return f"https://{bucket}.s3.amazonaws.com/{key}?versionId={version_id}"

    def ensure_public_prefix_access(self, *, bucket: str, prefix: str) -> bool:
        self._assert_public_policy_allowed(bucket)
        policy = self._load_bucket_policy(bucket)
        statement_id = self._statement_id(prefix)
        resource = f"arn:aws:s3:::{bucket}/{prefix}/*"
        expected_statement = {
            "Sid": statement_id,
            "Effect": "Allow",
            "Principal": "*",
            "Action": ["s3:GetObject"],
            "Resource": [resource],
        }
        statements = [item for item in policy["Statement"] if item.get("Sid") != statement_id]
        statements.append(expected_statement)
        changed = statements != policy["Statement"]
        if changed:
            self.client.put_bucket_policy(
                Bucket=bucket,
                Policy=json.dumps({"Version": "2012-10-17", "Statement": statements}),
            )
        return bool(changed)

    def disable_public_prefix_access(self, *, bucket: str, prefix: str) -> bool:
        policy = self._load_bucket_policy(bucket)
        statement_id = self._statement_id(prefix)
        statements = [item for item in policy["Statement"] if item.get("Sid") != statement_id]
        if statements == policy["Statement"]:
            return False
        if statements:
            self.client.put_bucket_policy(
                Bucket=bucket,
                Policy=json.dumps({"Version": "2012-10-17", "Statement": statements}),
            )
        else:
            self.client.delete_bucket_policy(Bucket=bucket)
        return True

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

    def _load_bucket_policy(self, bucket: str) -> dict[str, Any]:
        try:
            response = self.client.get_bucket_policy(Bucket=bucket)
        except Exception:
            return {"Version": "2012-10-17", "Statement": []}
        policy = response.get("Policy")
        if policy is None:
            return {"Version": "2012-10-17", "Statement": []}
        loaded = json.loads(str(policy))
        if isinstance(loaded, dict):
            return loaded
        return {"Version": "2012-10-17", "Statement": []}

    def _assert_public_policy_allowed(self, bucket: str) -> None:
        response = self.client.get_public_access_block(Bucket=bucket)
        config = response.get("PublicAccessBlockConfiguration", {})
        if bool(config.get("BlockPublicPolicy")) or bool(config.get("RestrictPublicBuckets")):
            raise ValueError(f"S3 bucket {bucket} blocks public bucket policies")

    @staticmethod
    def _statement_id(prefix: str) -> str:
        return "CordisPublicPrefix" + prefix.replace("/", "_")
