"""Request/response models used exclusively by API route handlers.

These were previously defined inline in routes.py. Centralizing them here
keeps the route file focused on HTTP handling and makes the schemas
reusable for testing and documentation.
"""

from __future__ import annotations

from relational_fraud_intelligence.domain.models import (
    AlertStatus,
    AnalysisResult,
    AppModel,
    CaseComment,
    CaseDisposition,
    CaseStatus,
    FraudAlert,
    FraudCase,
    InvestigationCase,
)

# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class ProviderPostureResponse(AppModel):
    requested_text_signal_provider: str
    active_text_signal_provider: str
    requested_reasoning_provider: str
    active_reasoning_provider: str
    requested_explanation_provider: str
    active_explanation_provider: str
    notes: list[str]


class HealthResponse(AppModel):
    status: str
    app_name: str
    environment: str
    database_status: str
    rate_limit_status: str
    provider_status: str
    rate_limit_backend: str
    seeded_scenarios: int
    seeded_operators: int
    provider_posture: ProviderPostureResponse


# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------


class AddCommentBody(AppModel):
    body: str


class AddCommentResult(AppModel):
    comment: CaseComment


class UpdateCaseStatusBody(AppModel):
    status: CaseStatus
    disposition: CaseDisposition | None = None
    resolution_notes: str | None = None


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------


class CreateCaseFromAlertResult(AppModel):
    alert: FraudAlert
    case: FraudCase


class UpdateAlertStatusBody(AppModel):
    status: AlertStatus
    linked_case_id: str | None = None


# ---------------------------------------------------------------------------
# Datasets
# ---------------------------------------------------------------------------


class DatasetResponse(AppModel):
    dataset_id: str
    name: str
    uploaded_at: str
    row_count: int
    status: str
    error_message: str | None = None


class DatasetListResponse(AppModel):
    datasets: list[DatasetResponse]


class TransactionIngestBody(AppModel):
    name: str = "api-ingestion"
    transactions: list[dict[str, object]]


class CreateCaseFromAnalysisResult(AppModel):
    analysis: AnalysisResult
    case: FraudCase
    linked_alerts: list[FraudAlert]


class CreateCaseFromInvestigationResult(AppModel):
    investigation: InvestigationCase
    case: FraudCase
    linked_alerts: list[FraudAlert]
