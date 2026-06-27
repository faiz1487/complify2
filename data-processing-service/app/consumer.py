"""Background SQS consumer for document processing."""

import logging
import threading
import time

from shared.database import SessionLocal
from shared.sqs_client import sqs_client

from app.processor import process_document_job
from app.sqs_parser import parse_sqs_body

logger = logging.getLogger(__name__)

_consumer_thread: threading.Thread | None = None
_stop_event = threading.Event()


def _poll_loop() -> None:
    logger.info("SQS consumer started")
    while not _stop_event.is_set():
        try:
            messages = sqs_client.receive_messages()
        except RuntimeError:
            logger.exception("SQS receive error")
            time.sleep(5)
            continue

        if not messages:
            continue

        for message in messages:
            receipt_handle = message["ReceiptHandle"]
            body = message.get("Body", "")
            jobs = parse_sqs_body(body)
            if not jobs:
                sqs_client.delete_message(receipt_handle)
                continue

            ack = True
            for job in jobs:
                db = SessionLocal()
                try:
                    if not process_document_job(db, job):
                        ack = False
                except Exception:
                    logger.exception("Job failed for s3_key=%s", job.get("s3_key"))
                finally:
                    db.close()

            if ack:
                try:
                    sqs_client.delete_message(receipt_handle)
                except RuntimeError:
                    logger.exception("Failed to delete SQS message")


def start_consumer() -> None:
    global _consumer_thread
    if _consumer_thread and _consumer_thread.is_alive():
        return
    _stop_event.clear()
    _consumer_thread = threading.Thread(target=_poll_loop, name="sqs-consumer", daemon=True)
    _consumer_thread.start()


def stop_consumer() -> None:
    _stop_event.set()
    if _consumer_thread and _consumer_thread.is_alive():
        _consumer_thread.join(timeout=10)
