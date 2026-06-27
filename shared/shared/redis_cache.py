"""Redis: query cache, sessions, rate limiting, and processing scratch data."""

import json
import logging
import uuid
from typing import Any

import redis
from redis.exceptions import RedisError

from shared.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

CACHE_PREFIX_META = "doc:meta:"
CACHE_PREFIX_SEARCH = "doc:search:"
CACHE_PREFIX_SESSION = "session:"
CACHE_PREFIX_RATE = "rate:"
CACHE_PREFIX_PROCESSING = "proc:"


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

    def _set_json(self, key: str, value: dict[str, Any], ttl: int | None = None) -> None:
        try:
            self.client.setex(
                key,
                ttl or settings.redis_ttl_seconds,
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

    def create_session(self, user_id: int | None = None, data: dict[str, Any] | None = None) -> str:
        session_id = uuid.uuid4().hex
        payload = {"user_id": user_id, **(data or {})}
        self._set_json(
            f"{CACHE_PREFIX_SESSION}{session_id}",
            payload,
            ttl=settings.redis_session_ttl_seconds,
        )
        return session_id

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        return self._get_json(f"{CACHE_PREFIX_SESSION}{session_id}")

    def delete_session(self, session_id: str) -> None:
        try:
            self.client.delete(f"{CACHE_PREFIX_SESSION}{session_id}")
        except RedisError:
            logger.exception("Redis delete failed for session")

    def check_rate_limit(self, scope: str, identifier: str, limit: int) -> bool:
        """Return True if request is allowed, False if rate limit exceeded."""
        key = f"{CACHE_PREFIX_RATE}{scope}:{identifier}"
        try:
            count = self.client.incr(key)
            if count == 1:
                self.client.expire(key, settings.redis_rate_limit_window_seconds)
            return count <= limit
        except RedisError:
            logger.exception("Rate limit check failed; allowing request")
            return True

    def set_processing_state(self, document_id: int, state: dict[str, Any]) -> None:
        self._set_json(f"{CACHE_PREFIX_PROCESSING}{document_id}", state, ttl=3600)

    def get_processing_state(self, document_id: int) -> dict[str, Any] | None:
        return self._get_json(f"{CACHE_PREFIX_PROCESSING}{document_id}")

    def clear_processing_state(self, document_id: int) -> None:
        try:
            self.client.delete(f"{CACHE_PREFIX_PROCESSING}{document_id}")
        except RedisError:
            logger.exception("Redis delete failed for processing state")


redis_cache = RedisCache()
