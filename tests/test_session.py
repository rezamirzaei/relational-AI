from __future__ import annotations

from pathlib import Path

import pytest

from relational_fraud_intelligence.infrastructure.persistence.session import (
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
