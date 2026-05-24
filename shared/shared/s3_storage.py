"""Amazon S3 document storage."""

import logging
import uuid
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from shared.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class S3Storage:
    def __init__(self) -> None:
        # Uses ECS task IAM role in AWS (no static credentials).
        client_kwargs: dict[str, str] = {"region_name": settings.aws_region}
        self._client = boto3.client("s3", **client_kwargs)

    @property
    def bucket(self) -> str:
        return settings.s3_bucket

    def build_s3_key(self, original_filename: str) -> str:
        safe_name = Path(original_filename).name.replace(" ", "_")
        unique_id = uuid.uuid4().hex[:12]
        return f"{settings.s3_upload_prefix}{unique_id}_{safe_name}"

    def upload_file(self, file_bytes: bytes, s3_key: str, content_type: str | None) -> str:
        extra_args: dict[str, str] = {}
        if content_type:
            extra_args["ContentType"] = content_type
        try:
            self._client.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=file_bytes,
                **extra_args,
            )
            return s3_key
        except (BotoCoreError, ClientError) as exc:
            logger.exception("S3 upload failed for key=%s", s3_key)
            raise RuntimeError(f"S3 upload failed: {exc}") from exc

    def get_object_uri(self, s3_key: str) -> str:
        return f"s3://{self.bucket}/{s3_key}"

    def head_object(self, s3_key: str) -> bool:
        try:
            self._client.head_object(Bucket=self.bucket, Key=s3_key)
            return True
        except ClientError:
            return False


s3_storage = S3Storage()
