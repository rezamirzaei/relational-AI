"""Investigation aggregate — investigation cases, metrics, graph analysis, leads."""

from __future__ import annotations

from pydantic import Field

from relational_fraud_intelligence.domain.base import AppModel
from relational_fraud_intelligence.domain.entity import EntityReference
from relational_fraud_intelligence.domain.enums import RiskLevel, TextSignalKind
from relational_fraud_intelligence.domain.scenario import ScenarioOverview
from relational_fraud_intelligence.domain.transaction import TransactionRecord


class TextSignal(AppModel):
    signal_id: str
    provider: str
    source_kind: TextSignalKind
    source_id: str
    label: str
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str


class GraphLink(AppModel):
    relation: str
    source: EntityReference
    target: EntityReference
    explanation: str


class RuleHit(AppModel):
    rule_code: str
    title: str
    weight: int = Field(ge=0)
    narrative: str
    evidence: list[EntityReference] = Field(default_factory=list)


class InvestigationMetrics(AppModel):
    total_transaction_volume: float = Field(ge=0.0)
    suspicious_transaction_volume: float = Field(ge=0.0)
    suspicious_transaction_count: int = Field(ge=0)
    shared_device_count: int = Field(ge=0)
    linked_customer_count: int = Field(ge=0)


class RelationalAIQueryBlueprint(AppModel):
    code: str
    description: str
    rule_pack: str
    derived_rule_paths: list[str] = Field(default_factory=list)


class RelationalAISemanticFinding(AppModel):
    finding_id: str
    blueprint_code: str
    title: str
    narrative: str
    rule_pack: str
    derived_rule_path: list[str] = Field(default_factory=list)
    semantic_concepts: list[str] = Field(default_factory=list)
    matched_entities: list[EntityReference] = Field(default_factory=list)
    evidence_edges: list[GraphLink] = Field(default_factory=list)
    supporting_transaction_ids: list[str] = Field(default_factory=list)
    risk_contribution: int = Field(ge=0, default=0)
    confidence: float = Field(ge=0.0, le=1.0)
    execution_mode: str


class RelationalAISemanticModelSummary(AppModel):
    concept_names: list[str] = Field(default_factory=list)
    relationship_names: list[str] = Field(default_factory=list)
    derived_rule_names: list[str] = Field(default_factory=list)
    query_blueprints: list[RelationalAIQueryBlueprint] = Field(default_factory=list)
    active_rule_packs: list[str] = Field(default_factory=list)
    semantic_findings: list[RelationalAISemanticFinding] = Field(default_factory=list)
    seeded_fact_count: int = Field(ge=0, default=0)
    compiled_type_count: int = Field(ge=0, default=0)
    compiled_relation_count: int = Field(ge=0, default=0)
    execution_posture: str


class ProviderSummary(AppModel):
    requested_reasoning_provider: str
    active_reasoning_provider: str
    requested_text_provider: str
    active_text_provider: str
    notes: list[str] = Field(default_factory=list)
    semantic_model: RelationalAISemanticModelSummary | None = None


class GraphAnalysisResult(AppModel):
    """Results from graph-based relationship analysis."""

    connected_components: int = Field(ge=0)
    density: float = Field(ge=0.0, le=1.0)
    highest_degree_entity: EntityReference | None = None
    highest_degree_score: int = Field(ge=0, default=0)
    community_count: int = Field(ge=0, default=0)
    shortest_path_length: int | None = None
    hub_entities: list[EntityReference] = Field(default_factory=list)
    risk_amplification_factor: float = Field(ge=1.0, default=1.0)


class InvestigationLead(AppModel):
    """An investigation-ready hypothesis assembled from related findings."""

    lead_id: str
    lead_type: str
    title: str
    severity: RiskLevel
    hypothesis: str
    narrative: str
    entities: list[EntityReference] = Field(default_factory=list)
    supporting_anomaly_ids: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    evidence: dict[str, object] = Field(default_factory=dict)


class InvestigationCase(AppModel):
    scenario: ScenarioOverview
    risk_level: RiskLevel
    total_risk_score: int = Field(ge=0, le=100)
    summary: str
    metrics: InvestigationMetrics
    provider_summary: ProviderSummary
    top_rule_hits: list[RuleHit]
    graph_links: list[GraphLink]
    text_signals: list[TextSignal]
    suspicious_transactions: list[TransactionRecord] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    investigation_leads: list[InvestigationLead] = Field(default_factory=list)
    graph_analysis: GraphAnalysisResult | None = None
