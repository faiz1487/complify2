"""Data processing service: SQS consumer, chunking, embeddings."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.consumer import start_consumer, stop_consumer
from shared.database import engine
from shared.redis_cache import redis_cache
from shared.sqs_client import sqs_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_consumer()
    logger.info("Data processing service started (queue=%s)", sqs_client.queue_url or "not configured")
    yield
    stop_consumer()
    logger.info("Data processing service shutting down")


app = FastAPI(
    title="Document Data Processing Service",
    version="2.0.0",
    lifespan=lifespan,
)


@app.get("/", tags=["info"])
def root() -> dict:
    return {
        "service": "data-processing-service",
        "port": 4003,
        "endpoints": {
            "health": "GET /health",
            "health_internal": "GET /health/processing",
        },
    }


@app.get("/health/processing", tags=["health"])
@app.get("/health", tags=["health"])
def health_check() -> dict:
    checks: dict[str, str] = {"api": "ok", "sqs": "ok" if sqs_client.queue_url else "not_configured"}
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        logger.exception("Database health check failed")
        checks["database"] = "error"

    checks["redis"] = "ok" if redis_cache.ping() else "error"
    status = "healthy" if checks.get("database") == "ok" and checks.get("redis") == "ok" else "degraded"
    return {"status": status, "service": "data-processing-service", "checks": checks}
