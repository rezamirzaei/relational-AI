from __future__ import annotations

from pydantic import Field

from relational_fraud_intelligence.domain.models import (
    AlertStatus,
    AppModel,
    FraudAlert,
    RiskLevel,
)


class CreateAlertCommand(AppModel):
    scenario_id: str
    rule_code: str
    title: str
    severity: RiskLevel
    narrative: str


class CreateAlertResult(AppModel):
    alert: FraudAlert


class UpdateAlertStatusCommand(AppModel):
    alert_id: str
    status: AlertStatus
    linked_case_id: str | None = None


class UpdateAlertStatusResult(AppModel):
    alert: FraudAlert


class ListAlertsQuery(AppModel):
    status: AlertStatus | None = None
    severity: RiskLevel | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class ListAlertsResult(AppModel):
    alerts: list[FraudAlert]
    total_count: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)


class GetAlertQuery(AppModel):
    alert_id: str


class GetAlertResult(AppModel):
    alert: FraudAlert
