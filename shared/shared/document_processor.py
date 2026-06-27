"""Text extraction, chunking, and embedding generation."""

import hashlib
import json
import logging
import math
import re
from typing import Any

from shared.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".log", ".xml", ".html", ".htm"}


def extract_text(file_name: str, content: bytes) -> str:
    suffix = file_name.lower()[file_name.rfind(".") :] if "." in file_name else ""
    if suffix in TEXT_EXTENSIONS:
        for encoding in ("utf-8", "latin-1"):
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                continue
        return content.decode("utf-8", errors="replace")

    return f"[Binary document: {file_name}, size={len(content)} bytes]"


def chunk_text(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []

    chunks: list[str] = []
    start = 0
    size = settings.chunk_size
    overlap = settings.chunk_overlap

    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            boundary = text.rfind("\n", start, end)
            if boundary > start + size // 2:
                end = boundary
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)

    return chunks or [text[:size]]


def _hash_embedding(text: str, dimensions: int = 384) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values: list[float] = []
    for i in range(dimensions):
        byte = digest[i % len(digest)]
        values.append((byte / 255.0) * 2 - 1)
    norm = math.sqrt(sum(v * v for v in values)) or 1.0
    return [v / norm for v in values]


def generate_embedding(text: str) -> list[float]:
    if settings.openai_api_key:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=settings.openai_api_key)
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=text[:8000],
            )
            return response.data[0].embedding
        except Exception:
            logger.exception("OpenAI embedding failed; using hash fallback")

    return _hash_embedding(text)


def estimate_tokens(text: str) -> int:
    return max(1, len(re.findall(r"\S+", text)))


def build_processed_payload(
    *,
    document_id: int,
    file_name: str,
    raw_s3_key: str,
    chunks: list[dict[str, Any]],
) -> str:
    return json.dumps(
        {
            "document_id": document_id,
            "file_name": file_name,
            "raw_s3_key": raw_s3_key,
            "chunk_count": len(chunks),
            "chunks": chunks,
        },
        default=str,
    )
