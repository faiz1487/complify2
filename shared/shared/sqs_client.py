"""Amazon SQS client for document processing events."""

import json
import logging
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from shared.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class SQSClient:
    def __init__(self) -> None:
        self._client = boto3.client("sqs", region_name=settings.aws_region)

    @property
    def queue_url(self) -> str:
        return settings.sqs_queue_url

    def publish_processing_job(
        self,
        *,
        document_id: int,
        s3_key: str,
        file_name: str,
    ) -> None:
        if not self.queue_url:
            logger.warning("SQS_QUEUE_URL not configured; skipping publish")
            return

        body = {
            "source": "upload-service",
            "document_id": document_id,
            "s3_key": s3_key,
            "file_name": file_name,
        }
        try:
            self._client.send_message(
                QueueUrl=self.queue_url,
                MessageBody=json.dumps(body),
            )
        except (BotoCoreError, ClientError) as exc:
            logger.exception("Failed to publish SQS message for document_id=%s", document_id)
            raise RuntimeError(f"SQS publish failed: {exc}") from exc

    def receive_messages(self) -> list[dict[str, Any]]:
        if not self.queue_url:
            return []

        try:
            response = self._client.receive_message(
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=settings.sqs_max_messages,
                WaitTimeSeconds=settings.sqs_poll_wait_seconds,
                MessageAttributeNames=["All"],
            )
        except (BotoCoreError, ClientError) as exc:
            logger.exception("SQS receive failed")
            raise RuntimeError(f"SQS receive failed: {exc}") from exc

        return response.get("Messages", [])

    def delete_message(self, receipt_handle: str) -> None:
        if not self.queue_url:
            return
        try:
            self._client.delete_message(
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle,
            )
        except (BotoCoreError, ClientError) as exc:
            logger.exception("SQS delete failed")
            raise RuntimeError(f"SQS delete failed: {exc}") from exc


sqs_client = SQSClient()
