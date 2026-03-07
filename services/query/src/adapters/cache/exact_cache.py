import hashlib
import json

import redis.asyncio as redis
import structlog

log = structlog.get_logger()

CACHE_TTL_SECONDS = 3600  # 1 hour


class ExactCache:
    """
    Layer 1 cache: SHA-256 of the normalized query string → cached answer.
    Hit rate: ~15-20% in practice (identical repeated queries).
    Latency: <1ms on hit.
    """

    def __init__(self, redis_url: str) -> None:
        self._redis = redis.from_url(redis_url, decode_responses=True)

    def _key(self, query: str) -> str:
        normalized = query.strip().lower()
        digest = hashlib.sha256(normalized.encode()).hexdigest()
        return f"cache:exact:{digest}"

    async def get(self, query: str) -> dict | None:
        raw = await self._redis.get(self._key(query))
        if raw is None:
            return None

        log.info("cache.exact_hit", query=query[:60])
        return json.loads(raw)

    async def set(self, query: str, answer: dict) -> None:
        await self._redis.setex(self._key(query), CACHE_TTL_SECONDS, json.dumps(answer))

    async def close(self) -> None:
        await self._redis.close()
