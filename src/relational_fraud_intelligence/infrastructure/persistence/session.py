from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


def build_engine(database_url: str, *, echo: bool = False) -> Engine:
    _prepare_sqlite_directory(database_url)

    engine_kwargs: dict[str, object] = {"echo": echo, "future": True}
    if database_url.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    if database_url.endswith(":memory:"):
        engine_kwargs["poolclass"] = StaticPool

    return create_engine(database_url, **engine_kwargs)


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def ping_database(session_factory: sessionmaker[Session]) -> bool:
    with session_factory() as session:
        session.execute(text("SELECT 1"))
    return True


def _prepare_sqlite_directory(database_url: str) -> None:
    sqlite_file_prefixes = (
        "sqlite+pysqlite:///./",
        "sqlite:///./",
        "sqlite+pysqlite:///",
        "sqlite:///",
    )
    if not database_url.startswith(sqlite_file_prefixes):
        return
    if database_url.endswith(":memory:"):
        return

    path_text = database_url.split("///", maxsplit=1)[1]
    database_path = Path(path_text)
    if not database_path.is_absolute():
        database_path = Path.cwd() / database_path
    database_path.parent.mkdir(parents=True, exist_ok=True)
