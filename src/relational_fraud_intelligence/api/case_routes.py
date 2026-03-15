"""Fraud case management endpoints."""

from fastapi import APIRouter, HTTPException, Request

from relational_fraud_intelligence.api._helpers import (
    AnalystDep,
    CasePriorityFilter,
    CaseStatusFilter,
    ContainerDep,
    PageParam,
    PageSizeParam,
    build_case_evidence_snapshot,
    case_detail_from_snapshot,
    create_case_with_source_links,
    to_case_dataset_detail,
    validate_case_source,
)
from relational_fraud_intelligence.application.dto.cases import (
    AddCaseCommentCommand,
    CreateCaseCommand,
    CreateCaseResult,
    GetCaseQuery,
    GetCaseResult,
    ListCasesQuery,
    ListCasesResult,
    UpdateCaseStatusCommand,
    UpdateCaseStatusResult,
)
from relational_fraud_intelligence.application.dto.investigation import (
    GetScenarioQuery,
    InvestigateScenarioCommand,
)
from relational_fraud_intelligence.application.dto.routes import (
    AddCommentBody,
    AddCommentResult,
    UpdateCaseStatusBody,
)
from relational_fraud_intelligence.domain.models import WorkflowSourceType

router = APIRouter()


@router.post(
    "/cases",
    response_model=CreateCaseResult,
    tags=["Cases"],
    summary="Create a fraud case",
    description=(
        "Creates a new fraud case linked to either a reference scenario or an uploaded dataset."
    ),
)
def create_case(
    command: CreateCaseCommand,
    request: Request,
    container: ContainerDep,
    principal: AnalystDep,
) -> CreateCaseResult:
    request.state.current_principal = principal
    request.state.audit_action = "create-case"
    request.state.audit_resource_type = "fraud-case"
    try:
        validate_case_source(command, container)
        created_case, _ = create_case_with_source_links(
            command=command,
            container=container,
            evidence_snapshot=build_case_evidence_snapshot(command, container),
        )
        return CreateCaseResult(case=created_case)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/cases",
    response_model=ListCasesResult,
    tags=["Cases"],
    summary="List fraud cases",
    description=(
        "Returns a paginated list of fraud cases with optional status, "
        "priority, and analyst filters."
    ),
)
def list_cases(
    request: Request,
    container: ContainerDep,
    principal: AnalystDep,
    status: CaseStatusFilter = None,
    priority: CasePriorityFilter = None,
    page: PageParam = 1,
    page_size: PageSizeParam = 20,
) -> ListCasesResult:
    request.state.current_principal = principal
    request.state.audit_action = "list-cases"
    request.state.audit_resource_type = "fraud-case"
    return container.case_service.list_cases(
        ListCasesQuery(status=status, priority=priority, page=page, page_size=page_size)
    )


@router.get(
    "/cases/{case_id}",
    response_model=GetCaseResult,
    tags=["Cases"],
    summary="Get case details",
)
def get_case(
    case_id: str,
    request: Request,
    container: ContainerDep,
    principal: AnalystDep,
) -> GetCaseResult:
    request.state.current_principal = principal
    request.state.audit_action = "get-case"
    request.state.audit_resource_type = "fraud-case"
    request.state.audit_resource_id = case_id
    try:
        case = container.case_service.get_case(GetCaseQuery(case_id=case_id)).case
        comments = container.case_service.list_comments(case_id)
        related_alerts = container.alert_service.list_alerts_for_source(
            source_type=case.source_type,
            source_id=case.source_id,
        )
        snapshot_result = case_detail_from_snapshot(
            case=case,
            comments=comments,
            related_alerts=related_alerts,
        )
        if snapshot_result is not None:
            return snapshot_result

        if case.source_type == WorkflowSourceType.DATASET:
            dataset = container.dataset_service.get_dataset(case.source_id)
            try:
                analysis = container.dataset_service.get_result(case.source_id)
            except LookupError:
                analysis = None

            return GetCaseResult(
                case=case,
                comments=comments,
                related_alerts=related_alerts,
                analysis=analysis,
                dataset=to_case_dataset_detail(dataset),
                dataset_transactions=container.dataset_service.get_transactions(case.source_id),
            )

        scenario_id = case.scenario_id or case.source_id
        scenario = container.scenario_catalog_service.get_scenario(
            GetScenarioQuery(scenario_id=scenario_id)
        ).scenario
        investigation = container.investigation_service.execute(
            InvestigateScenarioCommand(scenario_id=scenario_id)
        ).investigation

        return GetCaseResult(
            case=case,
            comments=comments,
            related_alerts=related_alerts,
            investigation=investigation,
            scenario_transactions=scenario.transactions,
            investigator_notes=scenario.investigator_notes,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch(
    "/cases/{case_id}/status",
    response_model=UpdateCaseStatusResult,
    tags=["Cases"],
    summary="Update case status",
    description=(
        "Transitions a case through its lifecycle: open, investigating, "
        "escalated, resolved, or closed."
    ),
)
def update_case_status(
    case_id: str,
    body: "UpdateCaseStatusBody",
    request: Request,
    container: ContainerDep,
    principal: AnalystDep,
) -> UpdateCaseStatusResult:
    request.state.current_principal = principal
    request.state.audit_action = "update-case-status"
    request.state.audit_resource_type = "fraud-case"
    request.state.audit_resource_id = case_id
    try:
        return container.case_service.update_status(
            UpdateCaseStatusCommand(
                case_id=case_id,
                status=body.status,
                disposition=body.disposition,
                resolution_notes=body.resolution_notes,
            )
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/cases/{case_id}/comments",
    response_model=AddCommentResult,
    tags=["Cases"],
    summary="Add a comment to a case",
    description="Appends an analyst note or observation to a fraud case.",
)
def add_case_comment(
    case_id: str,
    body: AddCommentBody,
    request: Request,
    container: ContainerDep,
    principal: AnalystDep,
) -> AddCommentResult:
    request.state.current_principal = principal
    request.state.audit_action = "add-case-comment"
    request.state.audit_resource_type = "fraud-case"
    request.state.audit_resource_id = case_id
    try:
        comment = container.case_service.add_comment(
            AddCaseCommentCommand(case_id=case_id, body=body.body),
            author_id=principal.user_id,
            author_name=principal.display_name,
        )
        return AddCommentResult(comment=comment)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

