from typing import Protocol

from relational_fraud_intelligence.application.dto.investigation import (
    GetScenarioQuery,
    GetScenarioResult,
    ListScenariosQuery,
    ListScenariosResult,
)


class ScenarioRepository(Protocol):
    def list_scenarios(self, query: ListScenariosQuery) -> ListScenariosResult:
        ...

    def get_scenario(self, query: GetScenarioQuery) -> GetScenarioResult:
        ...
