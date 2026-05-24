"""Document upload endpoint."""

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from shared.database import get_db
from shared.models import Document
from shared.redis_cache import redis_cache
from shared.s3_storage import s3_storage
from shared.schemas import DocumentMetadata, UploadResponse

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> UploadResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file not allowed")
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds maximum size of 50MB")

    s3_key = s3_storage.build_s3_key(file.filename)
    try:
        s3_storage.upload_file(content, s3_key, file.content_type)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    document = Document(file_name=file.filename, s3_key=s3_key)
    db.add(document)
    try:
        db.commit()
        db.refresh(document)
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to save document metadata")
        raise HTTPException(status_code=500, detail="Failed to save metadata") from exc

    metadata = DocumentMetadata(
        id=document.id,
        file_name=document.file_name,
        s3_key=document.s3_key,
        s3_uri=s3_storage.get_object_uri(document.s3_key),
        uploaded_at=document.uploaded_at,
    )
    redis_cache.cache_document_metadata(document.id, metadata.model_dump())
    redis_cache.invalidate_search(document.file_name)

    return UploadResponse(document=metadata)
