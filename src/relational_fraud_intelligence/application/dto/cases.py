from __future__ import annotations

from pydantic import Field

from relational_fraud_intelligence.domain.models import (
    AppModel,
    CaseDisposition,
    CasePriority,
    CaseStatus,
    FraudCase,
)


class CreateCaseCommand(AppModel):
    scenario_id: str
    title: str
    summary: str
    priority: CasePriority = CasePriority.MEDIUM
    assigned_analyst_id: str | None = None


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

