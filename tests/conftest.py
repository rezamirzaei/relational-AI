from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from relational_fraud_intelligence.infrastructure.persistence.repository import (
    SqlAlchemyScenarioRepository,
)
from relational_fraud_intelligence.infrastructure.persistence.security_repository import (
    SqlAlchemyAuditLogRepository,
    SqlAlchemyOperatorRepository,
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
    monkeypatch.setenv("RFI_JWT_SECRET", "test-secret-key-for-unit-tests-0001")
    monkeypatch.setenv("RFI_BOOTSTRAP_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("RFI_BOOTSTRAP_ADMIN_PASSWORD", "AdminPassword123!")
    monkeypatch.setenv("RFI_BOOTSTRAP_ANALYST_USERNAME", "analyst")
    monkeypatch.setenv("RFI_BOOTSTRAP_ANALYST_PASSWORD", "AnalystPassword123!")
    monkeypatch.setenv("RFI_RATE_LIMIT_BACKEND", "memory")


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


@pytest.fixture()
def operator_repository(
    session_factory: sessionmaker[Session],
) -> SqlAlchemyOperatorRepository:
    return SqlAlchemyOperatorRepository(session_factory)


@pytest.fixture()
def audit_repository(
    session_factory: sessionmaker[Session],
) -> SqlAlchemyAuditLogRepository:
    return SqlAlchemyAuditLogRepository(session_factory)
