"""Retrieval service: search documents and return metadata."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.routes import search
from shared.database import engine
from shared.redis_cache import redis_cache

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Retrieval service started")
    yield
    logger.info("Retrieval service shutting down")


app = FastAPI(
    title="Document Retrieval Service",
    version="2.0.0",
    lifespan=lifespan,
)

app.include_router(search.router, prefix="/api", tags=["search"])


@app.get("/", tags=["info"])
def root() -> dict:
    return {
        "service": "retrieval-service",
        "port": 4002,
        "endpoints": {
            "search": "GET /api/search/{filename}",
            "document_detail": "GET /api/documents/{document_id}",
            "health": "GET /health",
            "health_via_alb": "GET /health/retrieval",
        },
    }


@app.get("/health/retrieval", tags=["health"])
@app.get("/health", tags=["health"])
def health_check() -> dict:
    checks: dict[str, str] = {"api": "ok"}
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        logger.exception("Database health check failed")
        checks["database"] = "error"

    checks["redis"] = "ok" if redis_cache.ping() else "error"
    status = "healthy" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": status, "service": "retrieval-service", "checks": checks}
