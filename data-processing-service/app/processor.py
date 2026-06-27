"""Document processing pipeline invoked from SQS messages."""

import json
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from shared.document_processor import (
    build_processed_payload,
    chunk_text,
    estimate_tokens,
    extract_text,
    generate_embedding,
)
from shared.models import Document, DocumentChunk, DocumentStatus
from shared.redis_cache import redis_cache
from shared.s3_storage import s3_storage

logger = logging.getLogger(__name__)


def _resolve_document(db: Session, job: dict) -> Document | None:
    document_id = job.get("document_id")
    s3_key = job["s3_key"]

    if document_id:
        document = db.query(Document).filter(Document.id == document_id).first()
        if document:
            return document

    return db.query(Document).filter(Document.raw_s3_key == s3_key).first()


def process_document_job(db: Session, job: dict) -> bool:
    """Return True when the message can be acked; False to retry later."""
    document = _resolve_document(db, job)
    if document is None:
        logger.warning("No document record for s3_key=%s; will retry", job["s3_key"])
        return False

    if document.status == DocumentStatus.PROCESSED:
        logger.info("Document id=%s already processed", document.id)
        return True

    if document.status == DocumentStatus.PROCESSING:
        logger.info("Document id=%s already being processed", document.id)
        return True

    lock_acquired = redis_cache.client.set(
        f"lock:doc:{document.id}", "1", nx=True, ex=300
    )
    if not lock_acquired:
        logger.info("Document id=%s locked by another worker", document.id)
        return True

    document.status = DocumentStatus.PROCESSING
    document.error_message = None
    db.commit()

    redis_cache.set_processing_state(
        document.id,
        {"status": DocumentStatus.PROCESSING, "file_name": document.file_name},
    )

    raw_key = document.raw_s3_key
    processing_key = s3_storage.build_processing_key(raw_key)

    try:
        s3_storage.move_object(raw_key, processing_key)
        content = s3_storage.download_file(processing_key)

        text = extract_text(document.file_name, content)
        text_chunks = chunk_text(text)

        chunk_records: list[DocumentChunk] = []
        chunk_payloads: list[dict] = []

        for index, chunk_content in enumerate(text_chunks):
            embedding = generate_embedding(chunk_content)
            chunk = DocumentChunk(
                document_id=document.id,
                chunk_index=index,
                content=chunk_content,
                embedding=json.dumps(embedding),
                token_count=estimate_tokens(chunk_content),
            )
            chunk_records.append(chunk)
            chunk_payloads.append(
                {
                    "chunk_index": index,
                    "token_count": chunk.token_count,
                    "content_preview": chunk_content[:200],
                }
            )

        db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).delete()
        db.add_all(chunk_records)

        processed_key = s3_storage.build_processed_key(document.id, document.file_name)
        processed_json = build_processed_payload(
            document_id=document.id,
            file_name=document.file_name,
            raw_s3_key=processing_key,
            chunks=chunk_payloads,
        )
        s3_storage.upload_json(processed_key, processed_json)

        document.processed_s3_key = processed_key
        document.status = DocumentStatus.PROCESSED
        document.chunk_count = len(chunk_records)
        document.processed_at = datetime.now(timezone.utc)
        document.error_message = None
        db.commit()

        redis_cache.clear_processing_state(document.id)
        redis_cache.invalidate_search(document.file_name)
        logger.info("Processed document id=%s chunks=%s", document.id, document.chunk_count)
        return True

    except Exception as exc:
        db.rollback()
        document_id = document.id
        logger.exception("Processing failed for document id=%s", document_id)

        document = db.query(Document).filter(Document.id == document_id).first()
        if document:
            document.status = DocumentStatus.FAILED
            document.error_message = str(exc)[:2000]
            db.commit()

        try:
            if s3_storage.head_object(processing_key):
                failed_key = s3_storage.build_failed_key(raw_key)
                s3_storage.move_object(processing_key, failed_key)
        except Exception:
            logger.exception("Failed to move object to failed/ prefix")

        redis_cache.clear_processing_state(document.id)
        return True
