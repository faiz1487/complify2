"""Pydantic schemas for API requests and responses."""

from datetime import datetime

from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    id: int
    file_name: str
    raw_s3_key: str
    processed_s3_key: str | None = None
    raw_s3_uri: str
    processed_s3_uri: str | None = None
    status: str
    chunk_count: int = 0
    error_message: str | None = None
    uploaded_at: datetime
    processed_at: datetime | None = None


class UploadResponse(BaseModel):
    message: str = "Document uploaded successfully; processing queued"
    document: DocumentMetadata


class SearchResponse(BaseModel):
    found: bool
    document: DocumentMetadata | None = None


class ChunkSummary(BaseModel):
    chunk_index: int
    content_preview: str
    token_count: int


class DocumentDetailResponse(BaseModel):
    document: DocumentMetadata
    chunks: list[ChunkSummary] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    service: str
    checks: dict[str, str] = Field(default_factory=dict)
