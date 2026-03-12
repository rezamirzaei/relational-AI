from relational_fraud_intelligence.domain.models import (
    FraudScenario,
    RiskLevel,
    ScenarioOverview,
    ScenarioTag,
)


def build_scenario_overview(scenario: FraudScenario) -> ScenarioOverview:
    total_volume = round(sum(transaction.amount for transaction in scenario.transactions), 2)
    baseline_risk = RiskLevel.MEDIUM
    if ScenarioTag.SYNTHETIC_IDENTITY in scenario.tags:
        baseline_risk = RiskLevel.HIGH
    if len(scenario.transactions) >= 4 and ScenarioTag.DEVICE_RING in scenario.tags:
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
