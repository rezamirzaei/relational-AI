"""Dashboard models — aggregate stats, activity events, workflow stages."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from relational_fraud_intelligence.domain.base import AppModel


class ActivityEvent(AppModel):
    """A lightweight event for the dashboard activity feed."""

    event_type: str
    description: str
    actor: str | None = None
    occurred_at: datetime
    resource_id: str | None = None


class WorkflowStageSnapshot(AppModel):
    stage_id: str
    title: str
    description: str
    total_count: int = Field(ge=0, default=0)
    highlighted_count: int = Field(ge=0, default=0)
    highlighted_label: str


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
    completed_analyses: int = Field(ge=0, default=0)
    high_risk_analyses: int = Field(ge=0, default=0)
    workflow_stages: list[WorkflowStageSnapshot] = Field(default_factory=list)
    next_recommended_action: str = ""

