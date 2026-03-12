from __future__ import annotations

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload, sessionmaker

from relational_fraud_intelligence.application.dto.investigation import (
    GetScenarioQuery,
    GetScenarioResult,
    ListScenariosQuery,
    ListScenariosResult,
)
from relational_fraud_intelligence.application.services.scenario_overview_factory import (
    build_scenario_overview,
)
from relational_fraud_intelligence.infrastructure.persistence.mappers import to_domain_scenario
from relational_fraud_intelligence.infrastructure.persistence.models import (
    CustomerRecord,
    DeviceRecord,
    ScenarioRecord,
)


class SqlAlchemyScenarioRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def list_scenarios(self, query: ListScenariosQuery) -> ListScenariosResult:
        _ = query
        with self._session_factory() as session:
            scenarios = session.scalars(self._base_query().order_by(ScenarioRecord.title)).all()

        return ListScenariosResult(
            scenarios=[
                build_scenario_overview(to_domain_scenario(scenario)) for scenario in scenarios
            ]
        )

    def get_scenario(self, query: GetScenarioQuery) -> GetScenarioResult:
        with self._session_factory() as session:
            scenario = session.scalar(
                self._base_query().where(ScenarioRecord.scenario_id == query.scenario_id)
            )

        if scenario is None:
            raise LookupError(f"Unknown scenario '{query.scenario_id}'.")
        return GetScenarioResult(scenario=to_domain_scenario(scenario))

    @staticmethod
    def _base_query() -> Select[tuple[ScenarioRecord]]:
        return select(ScenarioRecord).options(
            selectinload(ScenarioRecord.customers).selectinload(CustomerRecord.accounts),
            selectinload(ScenarioRecord.customers).selectinload(CustomerRecord.linked_devices),
            selectinload(ScenarioRecord.accounts),
            selectinload(ScenarioRecord.devices).selectinload(DeviceRecord.linked_customers),
            selectinload(ScenarioRecord.merchants),
            selectinload(ScenarioRecord.transactions),
            selectinload(ScenarioRecord.investigator_notes),
        )
