"""Tests for the case lifecycle management service."""

from __future__ import annotations

import pytest

from relational_fraud_intelligence.application.dto.cases import (
    AddCaseCommentCommand,
    AssignCaseCommand,
    CreateCaseCommand,
    GetCaseQuery,
    ListCasesQuery,
    UpdateCaseStatusCommand,
)
from relational_fraud_intelligence.application.services.case_service import CaseService
from relational_fraud_intelligence.domain.models import (
    CaseDisposition,
    CasePriority,
    CaseStatus,
    RiskLevel,
    WorkflowSourceType,
)
from relational_fraud_intelligence.infrastructure.repositories.memory import InMemoryCaseRepository


@pytest.fixture()
def case_service() -> CaseService:
    return CaseService(InMemoryCaseRepository())


def test_create_case_returns_open_case_with_sla(case_service: CaseService) -> None:
    result = case_service.create_case(
        CreateCaseCommand(
            scenario_id="test-scenario",
            title="Suspected synthetic identity ring",
            summary="High-risk investigation flagged multiple shared devices.",
            priority=CasePriority.HIGH,
        ),
        risk_score=82,
        risk_level=RiskLevel.CRITICAL,
    )

    assert result.case.status == CaseStatus.OPEN
    assert result.case.risk_score == 82
    assert result.case.risk_level == RiskLevel.CRITICAL
    assert result.case.source_type == WorkflowSourceType.SCENARIO
    assert result.case.source_id == "test-scenario"
    assert result.case.sla_deadline is not None
    assert result.case.case_id


def test_update_case_status_to_resolved_sets_resolved_at(case_service: CaseService) -> None:
    create_result = case_service.create_case(
        CreateCaseCommand(
            scenario_id="test-scenario",
            title="Test case",
            summary="Test summary",
        ),
        risk_score=60,
        risk_level=RiskLevel.HIGH,
    )
    case_id = create_result.case.case_id

    result = case_service.update_status(
        UpdateCaseStatusCommand(
            case_id=case_id,
            status=CaseStatus.RESOLVED,
            disposition=CaseDisposition.CONFIRMED_FRAUD,
            resolution_notes="Device cluster confirmed as coordinated fraud ring.",
        )
    )

    assert result.case.status == CaseStatus.RESOLVED
    assert result.case.disposition == CaseDisposition.CONFIRMED_FRAUD
    assert result.case.resolved_at is not None
    assert result.case.resolution_notes == "Device cluster confirmed as coordinated fraud ring."


def test_assign_case_transitions_to_investigating(case_service: CaseService) -> None:
    create_result = case_service.create_case(
        CreateCaseCommand(
            scenario_id="test-scenario",
            title="Test case",
            summary="Test",
        )
    )
    case_id = create_result.case.case_id

    result = case_service.assign_case(
        AssignCaseCommand(case_id=case_id, analyst_id="user-123"),
        analyst_name="Jane Doe",
    )

    assert result.case.status == CaseStatus.INVESTIGATING
    assert result.case.assigned_analyst_id == "user-123"
    assert result.case.assigned_analyst_name == "Jane Doe"


def test_add_comment_increments_comment_count(case_service: CaseService) -> None:
    create_result = case_service.create_case(
        CreateCaseCommand(
            scenario_id="test-scenario",
            title="Test case",
            summary="Test",
        )
    )
    case_id = create_result.case.case_id

    comment = case_service.add_comment(
        AddCaseCommentCommand(case_id=case_id, body="Initial review looks suspicious."),
        author_id="analyst-1",
        author_name="Fraud Analyst",
    )

    assert comment.body == "Initial review looks suspicious."
    assert comment.author_name == "Fraud Analyst"

    fetched = case_service.get_case(GetCaseQuery(case_id=case_id))
    assert fetched.case.comment_count == 1


def test_list_cases_filters_by_status(case_service: CaseService) -> None:
    case_service.create_case(
        CreateCaseCommand(scenario_id="s1", title="Open case", summary="Open"),
    )
    create_result = case_service.create_case(
        CreateCaseCommand(scenario_id="s2", title="Resolved case", summary="Resolved"),
    )
    case_service.update_status(
        UpdateCaseStatusCommand(case_id=create_result.case.case_id, status=CaseStatus.RESOLVED)
    )

    open_result = case_service.list_cases(ListCasesQuery(status=CaseStatus.OPEN))
    assert open_result.total_count == 1
    assert open_result.cases[0].title == "Open case"


def test_get_nonexistent_case_raises_lookup_error(case_service: CaseService) -> None:
    with pytest.raises(LookupError):
        case_service.get_case(GetCaseQuery(case_id="does-not-exist"))


def test_create_case_can_use_dataset_source(case_service: CaseService) -> None:
    result = case_service.create_case(
        CreateCaseCommand(
            source_type=WorkflowSourceType.DATASET,
            source_id="dataset-123",
            title="Dataset case",
            summary="Velocity spikes detected in uploaded data.",
            risk_score=74,
            risk_level=RiskLevel.HIGH,
        )
    )

    assert result.case.source_type == WorkflowSourceType.DATASET
    assert result.case.source_id == "dataset-123"
    assert result.case.scenario_id is None
    assert result.case.risk_score == 74
    assert result.case.priority == CasePriority.HIGH
