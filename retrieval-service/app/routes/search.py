"""Document search and retrieval endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from shared.config import get_settings
from shared.database import get_db
from shared.models import Document, DocumentChunk
from shared.redis_cache import redis_cache
from shared.s3_storage import s3_storage
from shared.schemas import ChunkSummary, DocumentDetailResponse, DocumentMetadata, SearchResponse

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


def _client_identifier(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _to_metadata(doc: Document) -> DocumentMetadata:
    return DocumentMetadata(
        id=doc.id,
        file_name=doc.file_name,
        raw_s3_key=doc.raw_s3_key,
        processed_s3_key=doc.processed_s3_key,
        raw_s3_uri=s3_storage.get_object_uri(doc.raw_s3_key),
        processed_s3_uri=(
            s3_storage.get_object_uri(doc.processed_s3_key) if doc.processed_s3_key else None
        ),
        status=doc.status,
        chunk_count=doc.chunk_count,
        error_message=doc.error_message,
        uploaded_at=doc.uploaded_at,
        processed_at=doc.processed_at,
    )


@router.get("/search")
def search_missing_filename() -> None:
    raise HTTPException(
        status_code=400,
        detail="Filename required. Use GET /api/search/{filename}",
    )


@router.get("/search/{filename}", response_model=SearchResponse)
def search_document(
    filename: str,
    request: Request,
    db: Session = Depends(get_db),
) -> SearchResponse:
    if not redis_cache.check_rate_limit("search", _client_identifier(request), settings.search_rate_limit):
        raise HTTPException(status_code=429, detail="Search rate limit exceeded")

    if not filename.strip():
        raise HTTPException(status_code=400, detail="Filename is required")

    cached = redis_cache.get_search_response(filename)
    if cached is not None:
        if not cached.get("found"):
            return SearchResponse(found=False, document=None)
        return SearchResponse(
            found=True,
            document=DocumentMetadata(**cached["document"]),
        )

    document = (
        db.query(Document)
        .filter(Document.file_name == filename)
        .order_by(Document.uploaded_at.desc())
        .first()
    )

    if document is None:
        payload = {"found": False, "document": None}
        redis_cache.cache_search_response(filename, payload)
        return SearchResponse(found=False, document=None)

    metadata = _to_metadata(document)
    s3_key = document.processed_s3_key or document.raw_s3_key
    if not s3_storage.head_object(s3_key):
        logger.warning("S3 object missing for document id=%s key=%s", document.id, s3_key)

    response = SearchResponse(found=True, document=metadata)
    redis_cache.cache_search_response(
        filename,
        {"found": True, "document": metadata.model_dump()},
    )
    redis_cache.cache_document_metadata(document.id, metadata.model_dump())
    return response


@router.get("/documents/{document_id}", response_model=DocumentDetailResponse)
def get_document_detail(
    document_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> DocumentDetailResponse:
    if not redis_cache.check_rate_limit("search", _client_identifier(request), settings.search_rate_limit):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    document = db.query(Document).filter(Document.id == document_id).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    metadata = _to_metadata(document)
    chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
        .all()
    )
    chunk_summaries = [
        ChunkSummary(
            chunk_index=c.chunk_index,
            content_preview=c.content[:200],
            token_count=c.token_count,
        )
        for c in chunks
    ]

    redis_cache.cache_document_metadata(document_id, metadata.model_dump())
    return DocumentDetailResponse(document=metadata, chunks=chunk_summaries)
