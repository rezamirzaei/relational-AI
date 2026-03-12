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


class ScenarioTag(StrEnum):
    FRAUD = "fraud"
    SYNTHETIC_IDENTITY = "synthetic-identity"
    ACCOUNT_TAKEOVER = "account-takeover"
    DEVICE_RING = "device-ring"
    CROSS_BORDER = "cross-border"


class TransactionChannel(StrEnum):
    CARD_NOT_PRESENT = "card-not-present"
    WALLET = "wallet"
    BANK_TRANSFER = "bank-transfer"


class TransactionStatus(StrEnum):
    APPROVED = "approved"
    REVIEW = "review"
    DECLINED = "declined"


class TextSignalKind(StrEnum):
    INVESTIGATOR_NOTE = "investigator-note"
    MERCHANT_DESCRIPTION = "merchant-description"


class OperatorRole(StrEnum):
    ANALYST = "analyst"
    ADMIN = "admin"


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
    suspicious_transactions: list[TransactionRecord]
    recommended_actions: list[str]


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
