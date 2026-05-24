"""Document search endpoint."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from shared.database import get_db
from shared.models import Document
from shared.redis_cache import redis_cache
from shared.s3_storage import s3_storage
from shared.schemas import DocumentMetadata, SearchResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/search")
def search_missing_filename() -> None:
    raise HTTPException(
        status_code=400,
        detail="Filename required. Use GET /api/search/{filename} (example: /api/search/report.pdf)",
    )


def _to_metadata(doc: Document) -> DocumentMetadata:
    return DocumentMetadata(
        id=doc.id,
        file_name=doc.file_name,
        s3_key=doc.s3_key,
        s3_uri=s3_storage.get_object_uri(doc.s3_key),
        uploaded_at=doc.uploaded_at,
    )


@router.get("/search/{filename}", response_model=SearchResponse)
def search_document(
    filename: str,
    db: Session = Depends(get_db),
) -> SearchResponse:
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
    if not s3_storage.head_object(document.s3_key):
        logger.warning("S3 object missing for document id=%s key=%s", document.id, document.s3_key)

    response = SearchResponse(found=True, document=metadata)
    redis_cache.cache_search_response(
        filename,
        {"found": True, "document": metadata.model_dump()},
    )
    redis_cache.cache_document_metadata(document.id, metadata.model_dump())
    return response
