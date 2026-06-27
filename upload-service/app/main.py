"""Upload service: store raw documents in S3 and queue processing."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.routes import upload
from shared.database import Base, engine
from shared.redis_cache import redis_cache

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


def _init_database_schema(max_attempts: int = 10) -> None:
    """Create tables on ECS startup (RDS is in a private VPC)."""
    import time

    for attempt in range(1, max_attempts + 1):
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Database schema ready")
            return
        except Exception:
            logger.warning("DB not ready (attempt %s/%s)", attempt, max_attempts)
            if attempt == max_attempts:
                raise
            time.sleep(5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _init_database_schema()
    logger.info("Upload service started")
    yield
    logger.info("Upload service shutting down")


app = FastAPI(
    title="Document Upload Service",
    version="2.0.0",
    lifespan=lifespan,
)

app.include_router(upload.router, prefix="/api", tags=["upload"])


@app.get("/", tags=["info"])
def root() -> dict:
    return {
        "service": "upload-service",
        "port": 4000,
        "endpoints": {
            "upload": "POST /api/upload",
            "health": "GET /health",
            "health_via_alb": "GET /health/upload",
        },
    }


@app.get("/health/upload", tags=["health"])
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
    return {"status": status, "service": "upload-service", "checks": checks}
