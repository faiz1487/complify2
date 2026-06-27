"""Document upload endpoint."""

import logging

from fastapi import APIRouter, Depends, File, HTTPException, Header, Request, UploadFile, status
from sqlalchemy.orm import Session

from shared.database import get_db
from shared.models import Document, DocumentStatus
from shared.redis_cache import redis_cache
from shared.s3_storage import s3_storage
from shared.schemas import DocumentMetadata, UploadResponse
from shared.sqs_client import sqs_client
from shared.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB


def _client_identifier(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _to_metadata(document: Document) -> DocumentMetadata:
    return DocumentMetadata(
        id=document.id,
        file_name=document.file_name,
        raw_s3_key=document.raw_s3_key,
        processed_s3_key=document.processed_s3_key,
        raw_s3_uri=s3_storage.get_object_uri(document.raw_s3_key),
        processed_s3_uri=(
            s3_storage.get_object_uri(document.processed_s3_key)
            if document.processed_s3_key
            else None
        ),
        status=document.status,
        chunk_count=document.chunk_count,
        error_message=document.error_message,
        uploaded_at=document.uploaded_at,
        processed_at=document.processed_at,
    )


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    x_session_id: str | None = Header(default=None),
    x_user_id: int | None = Header(default=None),
) -> UploadResponse:
    if not redis_cache.check_rate_limit("upload", _client_identifier(request), settings.upload_rate_limit):
        raise HTTPException(status_code=429, detail="Upload rate limit exceeded")

    if x_session_id:
        session = redis_cache.get_session(x_session_id)
        if session is None:
            raise HTTPException(status_code=401, detail="Invalid or expired session")

    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file not allowed")
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds maximum size of 50MB")

    raw_s3_key = s3_storage.build_raw_key(file.filename)
    try:
        s3_storage.upload_file(content, raw_s3_key, file.content_type)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    document = Document(
        user_id=x_user_id,
        file_name=file.filename,
        raw_s3_key=raw_s3_key,
        status=DocumentStatus.PENDING,
    )
    db.add(document)
    try:
        db.commit()
        db.refresh(document)
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to save document metadata")
        raise HTTPException(status_code=500, detail="Failed to save metadata") from exc

    try:
        sqs_client.publish_processing_job(
            document_id=document.id,
            s3_key=raw_s3_key,
            file_name=file.filename,
        )
    except RuntimeError as exc:
        logger.error("SQS publish failed for document_id=%s: %s", document.id, exc)

    metadata = _to_metadata(document)
    redis_cache.cache_document_metadata(document.id, metadata.model_dump())
    redis_cache.invalidate_search(document.file_name)

    return UploadResponse(document=metadata)
