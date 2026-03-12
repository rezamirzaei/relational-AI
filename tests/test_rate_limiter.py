from relational_fraud_intelligence.infrastructure.rate_limit.memory import MemoryRateLimiter


def test_memory_rate_limiter_enforces_limit() -> None:
    limiter = MemoryRateLimiter()

    allowed_first, _ = limiter.consume("operator:123", limit=2, window_seconds=60)
    allowed_second, _ = limiter.consume("operator:123", limit=2, window_seconds=60)
    allowed_third, retry_after = limiter.consume("operator:123", limit=2, window_seconds=60)

    assert allowed_first is True
    assert allowed_second is True
    assert allowed_third is False
    assert retry_after >= 1
