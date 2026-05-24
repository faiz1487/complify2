"""Redis caching for document metadata and search responses."""

import json
import logging
from typing import Any

import redis
from redis.exceptions import RedisError

from shared.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

CACHE_PREFIX_META = "doc:meta:"
CACHE_PREFIX_SEARCH = "doc:search:"


class RedisCache:
    def __init__(self) -> None:
        self._client: redis.Redis | None = None

    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
        return self._client

    def ping(self) -> bool:
        try:
            return bool(self.client.ping())
        except RedisError:
            logger.exception("Redis ping failed")
            return False

    def _set_json(self, key: str, value: dict[str, Any]) -> None:
        try:
            self.client.setex(
                key,
                settings.redis_ttl_seconds,
                json.dumps(value, default=str),
            )
        except RedisError:
            logger.exception("Redis set failed for key=%s", key)

    def _get_json(self, key: str) -> dict[str, Any] | None:
        try:
            raw = self.client.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except (RedisError, json.JSONDecodeError):
            logger.exception("Redis get failed for key=%s", key)
            return None

    def cache_document_metadata(self, document_id: int, payload: dict[str, Any]) -> None:
        self._set_json(f"{CACHE_PREFIX_META}{document_id}", payload)

    def get_document_metadata(self, document_id: int) -> dict[str, Any] | None:
        return self._get_json(f"{CACHE_PREFIX_META}{document_id}")

    def cache_search_response(self, filename: str, payload: dict[str, Any]) -> None:
        normalized = filename.strip().lower()
        self._set_json(f"{CACHE_PREFIX_SEARCH}{normalized}", payload)

    def get_search_response(self, filename: str) -> dict[str, Any] | None:
        normalized = filename.strip().lower()
        return self._get_json(f"{CACHE_PREFIX_SEARCH}{normalized}")

    def invalidate_search(self, filename: str) -> None:
        normalized = filename.strip().lower()
        try:
            self.client.delete(f"{CACHE_PREFIX_SEARCH}{normalized}")
        except RedisError:
            logger.exception("Redis delete failed for search key")


redis_cache = RedisCache()
