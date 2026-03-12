from __future__ import annotations

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from relational_fraud_intelligence.application.dto.investigation import (
    GetScenarioQuery,
    ListScenariosQuery,
)
from relational_fraud_intelligence.infrastructure.persistence.repository import (
    SqlAlchemyScenarioRepository,
)
from relational_fraud_intelligence.infrastructure.persistence.seed import DatabaseInitializer
from relational_fraud_intelligence.infrastructure.seed.scenarios import build_seed_scenarios


def test_repository_lists_seeded_scenarios(
    scenario_repository: SqlAlchemyScenarioRepository,
) -> None:
    result = scenario_repository.list_scenarios(ListScenariosQuery())

    assert len(result.scenarios) == 3
    assert result.scenarios[0].scenario_id == "payroll-mule-funnel"


def test_database_initializer_is_idempotent(
    session_factory: sessionmaker[Session],
    engine: Engine,
) -> None:
    initializer = DatabaseInitializer(
        engine=engine,
        session_factory=session_factory,
        scenarios=build_seed_scenarios(),
    )

    inserted = initializer.seed_if_empty()
    result = SqlAlchemyScenarioRepository(session_factory).get_scenario(
        GetScenarioQuery(scenario_id="payroll-mule-funnel")
    )

    assert inserted == 0
    assert result.scenario.title == "Payroll Mule Funnel Through Transfer Network"
