from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class AppModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class EntityType(StrEnum):
    CUSTOMER = "customer"
    ACCOUNT = "account"
    DEVICE = "device"
    MERCHANT = "merchant"
    TRANSACTION = "transaction"
    NOTE = "note"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CaseStatus(StrEnum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CLOSED = "closed"


class CasePriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CaseDisposition(StrEnum):
    CONFIRMED_FRAUD = "confirmed-fraud"
    FALSE_POSITIVE = "false-positive"
    INCONCLUSIVE = "inconclusive"
    REFERRED_TO_LAW_ENFORCEMENT = "referred-to-law-enforcement"


class AlertStatus(StrEnum):
    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false-positive"


class ScenarioTag(StrEnum):
    FRAUD = "fraud"
    SYNTHETIC_IDENTITY = "synthetic-identity"
    ACCOUNT_TAKEOVER = "account-takeover"
    DEVICE_RING = "device-ring"
    CROSS_BORDER = "cross-border"
    MONEY_MULE = "money-mule"
    BUST_OUT = "bust-out"
    FIRST_PARTY = "first-party"


class TransactionChannel(StrEnum):
    CARD_NOT_PRESENT = "card-not-present"
    WALLET = "wallet"
    BANK_TRANSFER = "bank-transfer"
    CARD_PRESENT = "card-present"
    ACH = "ach"


class TransactionStatus(StrEnum):
    APPROVED = "approved"
    REVIEW = "review"
    DECLINED = "declined"
    PENDING = "pending"


class TextSignalKind(StrEnum):
    INVESTIGATOR_NOTE = "investigator-note"
    MERCHANT_DESCRIPTION = "merchant-description"


class DatasetStatus(StrEnum):
    UPLOADED = "uploaded"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class AnomalyType(StrEnum):
    BENFORD_VIOLATION = "benford-violation"
    STATISTICAL_OUTLIER = "statistical-outlier"
    VELOCITY_SPIKE = "velocity-spike"
    GRAPH_CLUSTER = "graph-cluster"
    ROUND_AMOUNT = "round-amount"


class OperatorRole(StrEnum):
    ANALYST = "analyst"
    ADMIN = "admin"


class WorkflowSourceType(StrEnum):
    SCENARIO = "scenario"
    DATASET = "dataset"


class EntityReference(AppModel):
    entity_type: EntityType
    entity_id: str
    display_name: str


class CustomerProfile(AppModel):
    customer_id: str
    full_name: str
    country_code: str = Field(min_length=2, max_length=2)
    segment: str
    declared_income_band: str
    linked_account_ids: list[str]
    linked_device_ids: list[str]
    watchlist_tags: list[str] = Field(default_factory=list)


class AccountProfile(AppModel):
    account_id: str
    customer_id: str
    opened_at: datetime
    current_balance: float
    average_monthly_inflow: float
    chargeback_count: int = Field(ge=0)
    manual_review_count: int = Field(ge=0)


class DeviceProfile(AppModel):
    device_id: str
    fingerprint: str
    ip_country_code: str = Field(min_length=2, max_length=2)
    linked_customer_ids: list[str]
    trust_score: float = Field(ge=0.0, le=1.0)


class MerchantProfile(AppModel):
    merchant_id: str
    display_name: str
    country_code: str = Field(min_length=2, max_length=2)
    category: str
    description: str


class TransactionRecord(AppModel):
    transaction_id: str
    customer_id: str
    account_id: str
    device_id: str
    merchant_id: str
    occurred_at: datetime
    amount: float = Field(gt=0.0)
    currency: str = Field(min_length=3, max_length=3)
    channel: TransactionChannel
    status: TransactionStatus


class InvestigatorNote(AppModel):
    note_id: str
    subject_customer_id: str
    author: str
    created_at: datetime
    body: str


class FraudScenario(AppModel):
    scenario_id: str
    title: str
    industry: str
    summary: str
    hypothesis: str
    tags: list[ScenarioTag]
    customers: list[CustomerProfile]
    accounts: list[AccountProfile]
    devices: list[DeviceProfile]
    merchants: list[MerchantProfile]
    transactions: list[TransactionRecord]
    investigator_notes: list[InvestigatorNote]


class ScenarioOverview(AppModel):
    scenario_id: str
    title: str
    industry: str
    summary: str
    hypothesis: str
    tags: list[ScenarioTag]
    transaction_count: int = Field(ge=0)
    total_volume: float = Field(ge=0.0)
    baseline_risk: RiskLevel


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


class ProviderSummary(AppModel):
    requested_reasoning_provider: str
    active_reasoning_provider: str
    requested_text_provider: str
    active_text_provider: str
    notes: list[str] = Field(default_factory=list)


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
    graph_analysis: GraphAnalysisResult | None = None


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


class FraudCase(AppModel):
    """A persistent fraud investigation case with lifecycle management."""

    case_id: str
    source_type: WorkflowSourceType = WorkflowSourceType.SCENARIO
    source_id: str
    scenario_id: str | None = None
    title: str
    status: CaseStatus = CaseStatus.OPEN
    priority: CasePriority = CasePriority.MEDIUM
    assigned_analyst_id: str | None = None
    assigned_analyst_name: str | None = None
    risk_score: int = Field(ge=0, le=100)
    risk_level: RiskLevel
    summary: str
    disposition: CaseDisposition | None = None
    resolution_notes: str | None = None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None = None
    sla_deadline: datetime | None = None
    comment_count: int = Field(ge=0, default=0)
    alert_count: int = Field(ge=0, default=0)


class CaseComment(AppModel):
    """A timestamped note attached to a fraud case by an analyst."""

    comment_id: str
    case_id: str
    author_id: str
    author_name: str
    body: str
    created_at: datetime


class FraudAlert(AppModel):
    """An auto-generated or manually created alert that may lead to a case."""

    alert_id: str
    source_type: WorkflowSourceType = WorkflowSourceType.SCENARIO
    source_id: str
    scenario_id: str | None = None
    rule_code: str
    title: str
    severity: RiskLevel
    status: AlertStatus = AlertStatus.NEW
    narrative: str
    assigned_analyst_id: str | None = None
    assigned_analyst_name: str | None = None
    linked_case_id: str | None = None
    created_at: datetime
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None


class ActivityEvent(AppModel):
    """A lightweight event for the dashboard activity feed."""

    event_type: str
    description: str
    actor: str | None = None
    occurred_at: datetime
    resource_id: str | None = None


class DashboardStats(AppModel):
    """Aggregate metrics for the analyst dashboard overview."""

    total_scenarios: int = Field(ge=0)
    total_cases: int = Field(ge=0)
    open_cases: int = Field(ge=0)
    critical_cases: int = Field(ge=0)
    total_alerts: int = Field(ge=0)
    unacknowledged_alerts: int = Field(ge=0)
    avg_risk_score: float = Field(ge=0.0, le=100.0)
    cases_by_status: dict[str, int] = Field(default_factory=dict)
    alerts_by_severity: dict[str, int] = Field(default_factory=dict)
    recent_activity: list[ActivityEvent] = Field(default_factory=list)
    risk_distribution: dict[str, int] = Field(default_factory=dict)
    total_datasets: int = Field(ge=0, default=0)
    total_transactions_analyzed: int = Field(ge=0, default=0)
    total_anomalies_found: int = Field(ge=0, default=0)


# ---------------------------------------------------------------------------
# Dataset & Analysis models — these power real data ingestion and detection
# ---------------------------------------------------------------------------


class UploadedTransaction(AppModel):
    """A single transaction row from a user-uploaded CSV or API ingestion."""

    row_index: int = Field(ge=0)
    transaction_id: str
    account_id: str
    amount: float = Field(gt=0.0)
    timestamp: datetime
    merchant: str = ""
    category: str = ""
    device_fingerprint: str = ""
    ip_country: str = ""
    channel: str = ""
    is_fraud_label: bool | None = None  # ground-truth label if available


class Dataset(AppModel):
    """A batch of uploaded transactions that can be analyzed."""

    dataset_id: str
    name: str
    uploaded_at: datetime
    row_count: int = Field(ge=0)
    status: DatasetStatus = DatasetStatus.UPLOADED
    error_message: str | None = None


class BenfordDigitResult(AppModel):
    """Benford's Law analysis for a single leading digit."""

    digit: int = Field(ge=1, le=9)
    expected_pct: float
    actual_pct: float
    deviation: float


class VelocitySpike(AppModel):
    """A detected spike in transaction velocity for an entity."""

    entity_id: str
    entity_type: str  # "account" or "merchant"
    window_start: datetime
    window_end: datetime
    transaction_count: int
    total_amount: float
    baseline_avg_count: float
    z_score: float


class AnomalyFlag(AppModel):
    """A single anomaly detected during analysis."""

    anomaly_id: str
    anomaly_type: AnomalyType
    severity: RiskLevel
    title: str
    description: str
    affected_entity_id: str
    affected_entity_type: str  # "account", "merchant", "transaction"
    score: float = Field(ge=0.0, le=1.0)
    evidence: dict[str, object] = Field(default_factory=dict)


class AnalysisResult(AppModel):
    """Complete analysis output for an uploaded dataset."""

    analysis_id: str
    dataset_id: str
    completed_at: datetime
    total_transactions: int = Field(ge=0)
    total_anomalies: int = Field(ge=0)
    risk_score: int = Field(ge=0, le=100)
    risk_level: RiskLevel

    # Benford's Law
    benford_chi_squared: float = Field(ge=0.0)
    benford_p_value: float = Field(ge=0.0, le=1.0)
    benford_is_suspicious: bool = False
    benford_digits: list[BenfordDigitResult] = Field(default_factory=list)

    # Statistical outliers
    outlier_count: int = Field(ge=0, default=0)
    outlier_pct: float = Field(ge=0.0, le=100.0, default=0.0)

    # Velocity spikes
    velocity_spikes: list[VelocitySpike] = Field(default_factory=list)

    # Graph analysis
    graph_analysis: GraphAnalysisResult | None = None

    # All anomaly flags
    anomalies: list[AnomalyFlag] = Field(default_factory=list)

    # Summary
    summary: str = ""


class OperatorPrincipal(AppModel):
    user_id: str
    username: str
    display_name: str
    role: OperatorRole
    is_active: bool


class AuditEvent(AppModel):
    event_id: int
    occurred_at: datetime
    request_id: str
    actor_user_id: str | None = None
    actor_username: str | None = None
    actor_role: OperatorRole | None = None
    action: str
    resource_type: str
    resource_id: str | None = None
    http_method: str
    path: str
    status_code: int
    ip_address: str | None = None
    user_agent: str | None = None
    details: dict[str, str] = Field(default_factory=dict)
