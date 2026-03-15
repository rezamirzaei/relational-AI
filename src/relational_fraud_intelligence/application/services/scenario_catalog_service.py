from relational_fraud_intelligence.application.dto.investigation import (
    GetScenarioQuery,
    GetScenarioResult,
    ListScenariosQuery,
    ListScenariosResult,
)
from relational_fraud_intelligence.application.ports.repositories import ScenarioRepository


class ScenarioCatalogService:
    def __init__(self, scenario_repository: ScenarioRepository) -> None:
        self._scenario_repository = scenario_repository

    async def list_scenarios(self, query: ListScenariosQuery) -> ListScenariosResult:
        return await self._scenario_repository.list_scenarios(query)

    async def get_scenario(self, query: GetScenarioQuery) -> GetScenarioResult:
        return await self._scenario_repository.get_scenario(query)
