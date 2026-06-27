"""SQS message parsing for S3 notifications and direct upload events."""

import json
import logging
import urllib.parse
from typing import Any

logger = logging.getLogger(__name__)


def parse_sqs_body(body: str) -> list[dict[str, Any]]:
    """Return normalized job dicts: document_id (optional), s3_key, file_name."""
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        logger.warning("Invalid SQS message body")
        return []

    jobs: list[dict[str, Any]] = []

    if "Records" in payload:
        for record in payload["Records"]:
            if record.get("eventSource") != "aws:s3":
                continue
            s3_info = record.get("s3", {})
            bucket = s3_info.get("bucket", {}).get("name")
            key = s3_info.get("object", {}).get("key")
            if not bucket or not key:
                continue
            key = urllib.parse.unquote_plus(key)
            file_name = key.split("/")[-1]
            jobs.append({"s3_key": key, "file_name": file_name, "bucket": bucket})
        return jobs

    if "s3_key" in payload:
        jobs.append(
            {
                "document_id": payload.get("document_id"),
                "s3_key": payload["s3_key"],
                "file_name": payload.get("file_name") or payload["s3_key"].split("/")[-1],
            }
        )

    return jobs
