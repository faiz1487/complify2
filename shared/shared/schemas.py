"""Pydantic schemas for API requests and responses."""

from datetime import datetime

from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    id: int
    file_name: str
    s3_key: str
    s3_uri: str
    uploaded_at: datetime


class UploadResponse(BaseModel):
    message: str = "Document uploaded successfully"
    document: DocumentMetadata


class SearchResponse(BaseModel):
    found: bool
    document: DocumentMetadata | None = None


class HealthResponse(BaseModel):
    status: str
    service: str
    checks: dict[str, str] = Field(default_factory=dict)
