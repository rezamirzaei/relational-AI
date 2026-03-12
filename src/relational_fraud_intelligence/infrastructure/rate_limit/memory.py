from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Lock


@dataclass(slots=True)
class CounterWindow:
    count: int
    resets_at: datetime


class MemoryRateLimiter:
    def __init__(self) -> None:
        self._lock = Lock()
        self._windows: dict[str, CounterWindow] = {}

    def consume(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        now = datetime.now(UTC)
        with self._lock:
            window = self._windows.get(key)
            if window is None or window.resets_at <= now:
                window = CounterWindow(
                    count=0,
                    resets_at=now + timedelta(seconds=window_seconds),
                )
                self._windows[key] = window

            window.count += 1
            remaining_seconds = max(1, int((window.resets_at - now).total_seconds()))
            return (window.count <= limit, remaining_seconds)

    def is_healthy(self) -> bool:
        return True
