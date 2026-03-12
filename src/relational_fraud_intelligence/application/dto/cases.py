from __future__ import annotations

from pydantic import Field, model_validator

from relational_fraud_intelligence.domain.models import (
    AppModel,
    CaseDisposition,
    CasePriority,
    CaseStatus,
    FraudCase,
    RiskLevel,
    WorkflowSourceType,
)


class CreateCaseCommand(AppModel):
    source_type: WorkflowSourceType = WorkflowSourceType.SCENARIO
    source_id: str | None = None
    scenario_id: str | None = None
    title: str
    summary: str
    priority: CasePriority | None = None
    assigned_analyst_id: str | None = None
    risk_score: int | None = Field(default=None, ge=0, le=100)
    risk_level: RiskLevel | None = None

    @model_validator(mode="after")
    def populate_source_fields(self) -> CreateCaseCommand:
        if self.source_type == WorkflowSourceType.SCENARIO:
            if self.source_id is None and self.scenario_id is not None:
                self.source_id = self.scenario_id
            if self.scenario_id is None and self.source_id is not None:
                self.scenario_id = self.source_id

        if self.source_id is None:
            raise ValueError("CreateCaseCommand requires source_id or scenario_id.")

        return self


class CreateCaseResult(AppModel):
    case: FraudCase


class UpdateCaseStatusCommand(AppModel):
    case_id: str
    status: CaseStatus
    disposition: CaseDisposition | None = None
    resolution_notes: str | None = None


class UpdateCaseStatusResult(AppModel):
    case: FraudCase


class AssignCaseCommand(AppModel):
    case_id: str
    analyst_id: str


class AssignCaseResult(AppModel):
    case: FraudCase


class AddCaseCommentCommand(AppModel):
    case_id: str
    body: str = Field(min_length=1, max_length=2000)


class ListCasesQuery(AppModel):
    status: CaseStatus | None = None
    priority: CasePriority | None = None
    assigned_analyst_id: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class ListCasesResult(AppModel):
    cases: list[FraudCase]
    total_count: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)


class GetCaseQuery(AppModel):
    case_id: str


class GetCaseResult(AppModel):
    case: FraudCase
