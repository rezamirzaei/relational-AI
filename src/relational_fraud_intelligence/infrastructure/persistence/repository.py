from __future__ import annotations

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

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
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def list_scenarios(self, query: ListScenariosQuery) -> ListScenariosResult:
        _ = query
        async with self._session_factory() as session:
            scenarios = (
                await session.scalars(self._base_query().order_by(ScenarioRecord.title))
            ).all()

        return ListScenariosResult(
            scenarios=[
                build_scenario_overview(to_domain_scenario(scenario)) for scenario in scenarios
            ]
        )

    async def get_scenario(self, query: GetScenarioQuery) -> GetScenarioResult:
        async with self._session_factory() as session:
            scenario = await session.scalar(
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
