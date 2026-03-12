from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import uuid4

from relational_fraud_intelligence.application.dto.cases import (
    AddCaseCommentCommand,
    AssignCaseCommand,
    AssignCaseResult,
    CreateCaseCommand,
    CreateCaseResult,
    GetCaseQuery,
    GetCaseResult,
    ListCasesQuery,
    ListCasesResult,
    UpdateCaseStatusCommand,
    UpdateCaseStatusResult,
)
from relational_fraud_intelligence.domain.models import (
    CaseComment,
    CasePriority,
    CaseStatus,
    FraudCase,
    RiskLevel,
    WorkflowSourceType,
)


class CaseRepository(Protocol):
    def create_case(self, case: FraudCase) -> None: ...
    def get_case(self, case_id: str) -> FraudCase | None: ...
    def update_case(self, case: FraudCase) -> None: ...
    def list_cases(
        self,
        *,
        status: CaseStatus | None = None,
        priority: CasePriority | None = None,
        assigned_analyst_id: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[FraudCase], int]: ...
    def add_comment(self, comment: CaseComment) -> None: ...
    def list_comments(self, case_id: str) -> list[CaseComment]: ...
    def count_by_status(self) -> dict[str, int]: ...
    def count_critical(self) -> int: ...


def _priority_from_risk(risk_level: RiskLevel) -> CasePriority:
    return {
        RiskLevel.LOW: CasePriority.LOW,
        RiskLevel.MEDIUM: CasePriority.MEDIUM,
        RiskLevel.HIGH: CasePriority.HIGH,
        RiskLevel.CRITICAL: CasePriority.CRITICAL,
    }[risk_level]


class CaseService:
    def __init__(self, case_repository: CaseRepository) -> None:
        self._repo = case_repository

    def create_case(
        self,
        command: CreateCaseCommand,
        *,
        risk_score: int = 50,
        risk_level: RiskLevel = RiskLevel.MEDIUM,
    ) -> CreateCaseResult:
        effective_risk_score = command.risk_score if command.risk_score is not None else risk_score
        effective_risk_level = command.risk_level if command.risk_level is not None else risk_level
        now = datetime.now(UTC)
        case = FraudCase(
            case_id=str(uuid4()),
            source_type=command.source_type,
            source_id=command.source_id or "",
            scenario_id=(
                command.scenario_id if command.source_type == WorkflowSourceType.SCENARIO else None
            ),
            title=command.title,
            status=CaseStatus.OPEN,
            priority=command.priority or _priority_from_risk(effective_risk_level),
            assigned_analyst_id=command.assigned_analyst_id,
            risk_score=effective_risk_score,
            risk_level=effective_risk_level,
            summary=command.summary,
            created_at=now,
            updated_at=now,
            sla_deadline=now
            + timedelta(
                hours=24 if effective_risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL} else 72
            ),
        )
        self._repo.create_case(case)
        return CreateCaseResult(case=case)

    def update_status(self, command: UpdateCaseStatusCommand) -> UpdateCaseStatusResult:
        case = self._repo.get_case(command.case_id)
        if case is None:
            raise LookupError(f"Case '{command.case_id}' not found.")

        now = datetime.now(UTC)
        case.status = command.status
        case.updated_at = now
        if command.disposition is not None:
            case.disposition = command.disposition
        if command.resolution_notes is not None:
            case.resolution_notes = command.resolution_notes
        if command.status in {CaseStatus.RESOLVED, CaseStatus.CLOSED}:
            case.resolved_at = now

        self._repo.update_case(case)
        return UpdateCaseStatusResult(case=case)

    def assign_case(
        self,
        command: AssignCaseCommand,
        analyst_name: str,
    ) -> AssignCaseResult:
        case = self._repo.get_case(command.case_id)
        if case is None:
            raise LookupError(f"Case '{command.case_id}' not found.")

        case.assigned_analyst_id = command.analyst_id
        case.assigned_analyst_name = analyst_name
        case.updated_at = datetime.now(UTC)
        if case.status == CaseStatus.OPEN:
            case.status = CaseStatus.INVESTIGATING

        self._repo.update_case(case)
        return AssignCaseResult(case=case)

    def add_comment(
        self,
        command: AddCaseCommentCommand,
        *,
        author_id: str,
        author_name: str,
    ) -> CaseComment:
        case = self._repo.get_case(command.case_id)
        if case is None:
            raise LookupError(f"Case '{command.case_id}' not found.")

        comment = CaseComment(
            comment_id=str(uuid4()),
            case_id=command.case_id,
            author_id=author_id,
            author_name=author_name,
            body=command.body,
            created_at=datetime.now(UTC),
        )
        self._repo.add_comment(comment)

        case.comment_count += 1
        case.updated_at = datetime.now(UTC)
        self._repo.update_case(case)

        return comment

    def get_case(self, query: GetCaseQuery) -> GetCaseResult:
        case = self._repo.get_case(query.case_id)
        if case is None:
            raise LookupError(f"Case '{query.case_id}' not found.")
        return GetCaseResult(case=case)

    def list_cases(self, query: ListCasesQuery) -> ListCasesResult:
        cases, total = self._repo.list_cases(
            status=query.status,
            priority=query.priority,
            assigned_analyst_id=query.assigned_analyst_id,
            page=query.page,
            page_size=query.page_size,
        )
        return ListCasesResult(
            cases=cases,
            total_count=total,
            page=query.page,
            page_size=query.page_size,
        )
