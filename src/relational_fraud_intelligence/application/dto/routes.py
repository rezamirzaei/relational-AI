"""Request/response models used exclusively by API route handlers.

These were previously defined inline in routes.py. Centralizing them here
keeps the route file focused on HTTP handling and makes the schemas
reusable for testing and documentation.
"""

from __future__ import annotations

from typing import Literal

from relational_fraud_intelligence.domain.models import (
    AlertStatus,
    AnalysisResult,
    AppModel,
    CaseComment,
    CaseDisposition,
    CaseStatus,
    DatasetStatus,
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
    status: Literal["ok", "degraded"]
    app_name: str
    environment: str
    database_status: Literal["ready", "unavailable"]
    rate_limit_status: Literal["ready", "degraded", "unavailable"]
    provider_status: Literal["ready", "degraded"]
    rate_limit_backend: str
    seeded_scenarios: int
    seeded_operators: int
    provider_posture: ProviderPostureResponse


class ReadinessResponse(AppModel):
    """Lightweight readiness probe response for orchestrators."""

    ready: bool
    database: Literal["ok", "unavailable"]


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
    status: DatasetStatus
    error_message: str | None = None


class DatasetListResponse(AppModel):
    datasets: list[DatasetResponse]
    total: int
    page: int
    page_size: int


class TransactionIngestBody(AppModel):
    name: str = "api-ingestion"
    transactions: list[dict[str, object]]


class AnalysisResponse(AppModel):
    analysis: AnalysisResult


class CreateCaseFromAnalysisResult(AppModel):
    analysis: AnalysisResult
    case: FraudCase
    linked_alerts: list[FraudAlert]


class CreateCaseFromInvestigationResult(AppModel):
    investigation: InvestigationCase
    case: FraudCase
    linked_alerts: list[FraudAlert]
