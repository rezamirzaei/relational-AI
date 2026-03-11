from relational_fraud_intelligence.application.dto.investigation import (
    GetScenarioQuery,
    GetScenarioResult,
    ListScenariosQuery,
    ListScenariosResult,
)
from relational_fraud_intelligence.domain.models import FraudScenario, RiskLevel, ScenarioOverview, ScenarioTag
from relational_fraud_intelligence.infrastructure.config.demo_data import build_demo_scenarios


def to_scenario_overview(scenario: FraudScenario) -> ScenarioOverview:
    total_volume = round(sum(transaction.amount for transaction in scenario.transactions), 2)
    baseline_risk = RiskLevel.MEDIUM
    if ScenarioTag.SYNTHETIC_IDENTITY in scenario.tags:
        baseline_risk = RiskLevel.HIGH
    if len(scenario.transactions) >= 5 and ScenarioTag.DEVICE_RING in scenario.tags:
        baseline_risk = RiskLevel.CRITICAL

    return ScenarioOverview(
        scenario_id=scenario.scenario_id,
        title=scenario.title,
        industry=scenario.industry,
        summary=scenario.summary,
        hypothesis=scenario.hypothesis,
        tags=scenario.tags,
        transaction_count=len(scenario.transactions),
        total_volume=total_volume,
        baseline_risk=baseline_risk,
    )


class DemoScenarioRepository:
    def __init__(self) -> None:
        self._scenarios = {scenario.scenario_id: scenario for scenario in build_demo_scenarios()}

    def list_scenarios(self, query: ListScenariosQuery) -> ListScenariosResult:
        _ = query
        return ListScenariosResult(
            scenarios=[to_scenario_overview(scenario) for scenario in self._scenarios.values()]
        )

    def get_scenario(self, query: GetScenarioQuery) -> GetScenarioResult:
        scenario = self._scenarios.get(query.scenario_id)
        if scenario is None:
            raise LookupError(f"Unknown scenario '{query.scenario_id}'.")
        return GetScenarioResult(scenario=scenario)
