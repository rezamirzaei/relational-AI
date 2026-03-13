import pytest
from redis.exceptions import RedisError

from relational_fraud_intelligence.infrastructure.rate_limit.memory import MemoryRateLimiter
from relational_fraud_intelligence.infrastructure.rate_limit.redis_backend import (
    RedisRateLimiter,
)


def test_memory_rate_limiter_enforces_limit() -> None:
    limiter = MemoryRateLimiter()

    allowed_first, _ = limiter.consume("operator:123", limit=2, window_seconds=60)
    allowed_second, _ = limiter.consume("operator:123", limit=2, window_seconds=60)
    allowed_third, retry_after = limiter.consume("operator:123", limit=2, window_seconds=60)

    assert allowed_first is True
    assert allowed_second is True
    assert allowed_third is False
    assert retry_after >= 1


class _FakeRedisClient:
    def __init__(
        self,
        *,
        incr_value: int = 1,
        ttl_value: int = 60,
        ping_value: bool = True,
        incr_error: Exception | None = None,
        ping_error: Exception | None = None,
    ) -> None:
        self.incr_value = incr_value
        self.ttl_value = ttl_value
        self.ping_value = ping_value
        self.incr_error = incr_error
        self.ping_error = ping_error
        self.expire_calls: list[tuple[str, int]] = []
        self.closed = False

    def incr(self, _key: str) -> int:
        if self.incr_error is not None:
            raise self.incr_error
        return self.incr_value

    def expire(self, key: str, ttl_seconds: int) -> None:
        self.expire_calls.append((key, ttl_seconds))

    def ttl(self, _key: str) -> int:
        return self.ttl_value

    def ping(self) -> bool:
        if self.ping_error is not None:
            raise self.ping_error
        return self.ping_value

    def close(self) -> None:
        self.closed = True


def test_redis_rate_limiter_sets_expiry_for_new_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _FakeRedisClient(incr_value=1, ttl_value=42)
    monkeypatch.setattr(
        "relational_fraud_intelligence.infrastructure.rate_limit.redis_backend.Redis.from_url",
        lambda _url, decode_responses: client,
    )
    limiter = RedisRateLimiter("redis://unit-test")

    allowed, retry_after = limiter.consume("operator:123", limit=2, window_seconds=60)

    assert allowed is True
    assert retry_after == 42
    assert client.expire_calls == [("rate-limit:operator:123", 60)]


def test_redis_rate_limiter_uses_window_when_ttl_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _FakeRedisClient(incr_value=3, ttl_value=-1)
    monkeypatch.setattr(
        "relational_fraud_intelligence.infrastructure.rate_limit.redis_backend.Redis.from_url",
        lambda _url, decode_responses: client,
    )
    limiter = RedisRateLimiter("redis://unit-test")

    allowed, retry_after = limiter.consume("operator:123", limit=2, window_seconds=90)

    assert allowed is False
    assert retry_after == 90


def test_redis_rate_limiter_wraps_backend_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _FakeRedisClient(incr_error=RedisError("boom"))
    monkeypatch.setattr(
        "relational_fraud_intelligence.infrastructure.rate_limit.redis_backend.Redis.from_url",
        lambda _url, decode_responses: client,
    )
    limiter = RedisRateLimiter("redis://unit-test")

    with pytest.raises(RuntimeError, match="rate-limit backend is unavailable"):
        limiter.consume("operator:123", limit=2, window_seconds=60)


def test_redis_rate_limiter_reports_health_and_closes_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    healthy_client = _FakeRedisClient(ping_value=True)
    monkeypatch.setattr(
        "relational_fraud_intelligence.infrastructure.rate_limit.redis_backend.Redis.from_url",
        lambda _url, decode_responses: healthy_client,
    )
    healthy_limiter = RedisRateLimiter("redis://unit-test")

    assert healthy_limiter.is_healthy() is True
    healthy_limiter.close()
    assert healthy_client.closed is True


def test_redis_rate_limiter_reports_unhealthy_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _FakeRedisClient(ping_error=RedisError("boom"))
    monkeypatch.setattr(
        "relational_fraud_intelligence.infrastructure.rate_limit.redis_backend.Redis.from_url",
        lambda _url, decode_responses: client,
    )
    limiter = RedisRateLimiter("redis://unit-test")

    assert limiter.is_healthy() is False
