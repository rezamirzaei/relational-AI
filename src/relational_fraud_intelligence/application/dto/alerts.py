from __future__ import annotations

from pydantic import Field, model_validator

from relational_fraud_intelligence.domain.models import (
    AlertStatus,
    AppModel,
    FraudAlert,
    RiskLevel,
    WorkflowSourceType,
)


class CreateAlertCommand(AppModel):
    source_type: WorkflowSourceType = WorkflowSourceType.SCENARIO
    source_id: str | None = None
    scenario_id: str | None = None
    rule_code: str
    title: str
    severity: RiskLevel
    narrative: str

    @model_validator(mode="after")
    def populate_source_fields(self) -> CreateAlertCommand:
        if self.source_type == WorkflowSourceType.SCENARIO:
            if self.source_id is None and self.scenario_id is not None:
                self.source_id = self.scenario_id
            if self.scenario_id is None and self.source_id is not None:
                self.scenario_id = self.source_id

        if self.source_id is None:
            raise ValueError("CreateAlertCommand requires source_id or scenario_id.")

        return self


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
