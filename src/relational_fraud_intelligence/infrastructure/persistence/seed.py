from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from relational_fraud_intelligence.domain.models import FraudScenario
from relational_fraud_intelligence.infrastructure.persistence.base import Base
from relational_fraud_intelligence.infrastructure.persistence.mappers import to_scenario_record
from relational_fraud_intelligence.infrastructure.persistence.models import ScenarioRecord


@dataclass(slots=True)
class SeedResult:
    created_schema: bool
    inserted_scenarios: int


class DatabaseInitializer:
    def __init__(
        self,
        engine: Engine,
        session_factory: sessionmaker[Session],
        scenarios: tuple[FraudScenario, ...],
    ) -> None:
        self._engine = engine
        self._session_factory = session_factory
        self._scenarios = scenarios

    def initialize(self, *, create_schema: bool, seed_if_empty: bool) -> SeedResult:
        created_schema = False
        if create_schema:
            Base.metadata.create_all(self._engine)
            created_schema = True

        inserted_scenarios = 0
        if seed_if_empty:
            inserted_scenarios = self.seed_if_empty()

        return SeedResult(
            created_schema=created_schema,
            inserted_scenarios=inserted_scenarios,
        )

    def seed_if_empty(self) -> int:
        with self._session_factory.begin() as session:
            existing_count = session.scalar(select(func.count()).select_from(ScenarioRecord))
            if existing_count:
                return 0

            for scenario in self._scenarios:
                session.add(to_scenario_record(scenario))

        return len(self._scenarios)
