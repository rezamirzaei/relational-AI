from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from relational_fraud_intelligence.infrastructure.persistence.session import (
    ping_database,
    prepare_database_url,
)


async def test_prepare_database_url_creates_parent_directory_for_relative_sqlite_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    prepare_database_url("sqlite+pysqlite:///./nested/path/test.db")

    assert (tmp_path / "nested" / "path").is_dir()


async def test_prepare_database_url_ignores_in_memory_sqlite_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    prepare_database_url("sqlite+pysqlite:///:memory:")

    assert not (tmp_path / ":memory:").exists()


async def test_ping_database_returns_false_on_failure() -> None:
    """ping_database must return False (not raise) when the DB is unreachable."""
    from collections.abc import AsyncIterator
    from contextlib import asynccontextmanager
    from typing import Any

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(side_effect=RuntimeError("connection refused"))

    @asynccontextmanager
    async def _fake_session() -> AsyncIterator[Any]:
        yield mock_session

    # async_sessionmaker.__call__ returns an async context manager (not a coroutine)
    factory = _fake_session

    result = await ping_database(factory)
    assert result is False
