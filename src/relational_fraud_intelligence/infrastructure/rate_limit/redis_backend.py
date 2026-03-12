from __future__ import annotations

from collections.abc import Callable
from typing import cast

from redis import Redis
from redis.exceptions import RedisError


class RedisRateLimiter:
    def __init__(self, redis_url: str) -> None:
        self._client: Redis = Redis.from_url(redis_url, decode_responses=True)

    def consume(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        window_key = f"rate-limit:{key}"
        try:
            value = int(cast(int, self._client.incr(window_key)))
            if value == 1:
                self._client.expire(window_key, window_seconds)
            ttl = self._client.ttl(window_key)
        except RedisError as exc:
            raise RuntimeError("The shared rate-limit backend is unavailable.") from exc

        remaining_seconds = max(1, ttl if isinstance(ttl, int) and ttl > 0 else window_seconds)
        return (value <= limit, remaining_seconds)

    def is_healthy(self) -> bool:
        try:
            return bool(self._client.ping())
        except RedisError:
            return False

    def close(self) -> None:
        close = cast(Callable[[], object] | None, getattr(self._client, "close", None))
        if close is not None:
            close()
