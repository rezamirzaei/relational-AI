"""Database engine and session factory construction — async SQLAlchemy.

This module provides asynchronous SQLAlchemy ``AsyncEngine`` and
``AsyncSession`` objects, enabling native ``async/await`` I/O throughout
the repository and service layers.

For SQLite the ``aiosqlite`` driver is used; for PostgreSQL the
``psycopg`` async driver is used.  Alembic migrations intentionally keep
a **synchronous** engine (via ``engine_from_config``) since the Alembic
CLI is not an async context.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import event, text
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool


def build_engine(database_url: str, *, echo: bool = False) -> AsyncEngine:
    database_url = _normalise_url_for_async(database_url)
    prepare_database_url(database_url)

    engine_kwargs: dict[str, object] = {"echo": echo}
    if database_url.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    if database_url.endswith(":memory:"):
        engine_kwargs["poolclass"] = StaticPool

    engine = create_async_engine(database_url, **engine_kwargs)
    if database_url.startswith("sqlite"):
        _enable_sqlite_foreign_keys(engine)
    return engine


def build_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


async def ping_database(session_factory: async_sessionmaker[AsyncSession]) -> bool:
    async with session_factory() as session:
        await session.execute(text("SELECT 1"))
    return True


def prepare_database_url(database_url: str) -> None:
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite":
        return

    database_name = url.database
    if database_name in {None, "", ":memory:"}:
        return

    assert database_name is not None
    database_path = Path(database_name)
    if not database_path.is_absolute():
        database_path = Path.cwd() / database_path
    database_path.parent.mkdir(parents=True, exist_ok=True)


def _normalise_url_for_async(database_url: str) -> str:
    """Swap synchronous SQLite drivers for their async equivalents."""
    if database_url.startswith("sqlite+pysqlite://"):
        return database_url.replace("sqlite+pysqlite://", "sqlite+aiosqlite://", 1)
    if database_url.startswith("sqlite://"):
        return database_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    return database_url


def _enable_sqlite_foreign_keys(engine: AsyncEngine) -> None:
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record) -> None:  # type: ignore[no-untyped-def]
        del connection_record
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
        finally:
            cursor.close()
