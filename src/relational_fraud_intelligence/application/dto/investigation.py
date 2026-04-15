from pydantic import Field

from relational_fraud_intelligence.domain.models import (
    AppModel,
    FraudScenario,
    GraphLink,
    InvestigationCase,
    InvestigationMetrics,
    RelationalAISemanticModelSummary,
    RiskLevel,
    RuleHit,
    ScenarioOverview,
    TextSignal,
    TransactionRecord,
)


class ListScenariosQuery(AppModel):
    pass


class ListScenariosResult(AppModel):
    scenarios: list[ScenarioOverview]


class GetScenarioQuery(AppModel):
    scenario_id: str


class GetScenarioResult(AppModel):
    scenario: FraudScenario


class InvestigateScenarioCommand(AppModel):
    scenario_id: str


class InvestigateScenarioDraftCommand(AppModel):
    scenario: FraudScenario


class ScoreTextSignalsCommand(AppModel):
    scenario: FraudScenario


class ScoreTextSignalsResult(AppModel):
    requested_provider: str
    active_provider: str
    notes: list[str] = Field(default_factory=list)
    signals: list[TextSignal]


class ReasonAboutRiskCommand(AppModel):
    scenario: FraudScenario
    text_signals: list[TextSignal]


class ReasonAboutRiskResult(AppModel):
    requested_provider: str
    active_provider: str
    provider_notes: list[str] = Field(default_factory=list)
    semantic_model: RelationalAISemanticModelSummary | None = None
    risk_level: RiskLevel
    total_risk_score: int
    summary: str
    metrics: InvestigationMetrics
    top_rule_hits: list[RuleHit]
    graph_links: list[GraphLink]
    suspicious_transactions: list[TransactionRecord]
    recommended_actions: list[str]


class AssembleInvestigationCommand(AppModel):
    scenario_overview: ScenarioOverview
    text_result: ScoreTextSignalsResult
    reasoning_result: ReasonAboutRiskResult


class InvestigateScenarioResult(AppModel):
    investigation: InvestigationCase
