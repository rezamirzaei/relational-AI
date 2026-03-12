from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from relational_fraud_intelligence.infrastructure.persistence.repository import (
    SqlAlchemyScenarioRepository,
)
from relational_fraud_intelligence.infrastructure.persistence.seed import DatabaseInitializer
from relational_fraud_intelligence.infrastructure.persistence.session import (
    build_engine,
    build_session_factory,
)
from relational_fraud_intelligence.infrastructure.seed.scenarios import build_seed_scenarios


@pytest.fixture(autouse=True)
def test_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RFI_DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("RFI_DATABASE_AUTO_CREATE_SCHEMA", "true")
    monkeypatch.setenv("RFI_SEED_SCENARIOS_ON_STARTUP", "true")
    monkeypatch.setenv("RFI_TEXT_SIGNAL_PROVIDER", "keyword")
    monkeypatch.setenv("RFI_REASONING_PROVIDER", "local-rule-engine")


@pytest.fixture()
def engine() -> Generator[Engine, None, None]:
    engine = build_engine("sqlite+pysqlite:///:memory:")
    yield engine
    engine.dispose()


@pytest.fixture()
def session_factory(engine: Engine) -> sessionmaker[Session]:
    session_factory = build_session_factory(engine)
    initializer = DatabaseInitializer(
        engine=engine,
        session_factory=session_factory,
        scenarios=build_seed_scenarios(),
    )
    initializer.initialize(create_schema=True, seed_if_empty=True)
    return session_factory


@pytest.fixture()
def scenario_repository(
    session_factory: sessionmaker[Session],
) -> SqlAlchemyScenarioRepository:
    return SqlAlchemyScenarioRepository(session_factory)
