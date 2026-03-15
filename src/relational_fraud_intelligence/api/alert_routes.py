"""Fraud alert triage endpoints."""

from fastapi import APIRouter, HTTPException, Request

from relational_fraud_intelligence.api._helpers import (
    AlertStatusFilter,
    AnalystDep,
    ContainerDep,
    PageParam,
    PageSizeParam,
    RiskLevelFilter,
    build_case_command_from_alert,
    build_case_evidence_snapshot,
    create_case_with_source_links,
    sync_case_alert_counts,
    validate_case_source,
)
from relational_fraud_intelligence.application.dto.alerts import (
    GetAlertQuery,
    ListAlertsQuery,
    ListAlertsResult,
    UpdateAlertStatusCommand,
    UpdateAlertStatusResult,
)
from relational_fraud_intelligence.application.dto.cases import GetCaseQuery
from relational_fraud_intelligence.application.dto.routes import (
    CreateCaseFromAlertResult,
    UpdateAlertStatusBody,
)
from relational_fraud_intelligence.domain.models import AlertStatus

router = APIRouter()


@router.get(
    "/alerts",
    response_model=ListAlertsResult,
    tags=["Alerts"],
    summary="List fraud alerts",
    description=(
        "Returns a paginated list of fraud alerts with optional status and severity filters."
    ),
)
def list_alerts(
    request: Request,
    container: ContainerDep,
    principal: AnalystDep,
    status: AlertStatusFilter = None,
    severity: RiskLevelFilter = None,
    page: PageParam = 1,
    page_size: PageSizeParam = 20,
) -> ListAlertsResult:
    request.state.current_principal = principal
    request.state.audit_action = "list-alerts"
    request.state.audit_resource_type = "fraud-alert"
    return container.alert_service.list_alerts(
        ListAlertsQuery(status=status, severity=severity, page=page, page_size=page_size)
    )


@router.patch(
    "/alerts/{alert_id}",
    response_model=UpdateAlertStatusResult,
    tags=["Alerts"],
    summary="Update alert status",
    description="Transitions an alert status and optionally links it to a case.",
)
def update_alert_status(
    alert_id: str,
    body: UpdateAlertStatusBody,
    request: Request,
    container: ContainerDep,
    principal: AnalystDep,
) -> UpdateAlertStatusResult:
    request.state.current_principal = principal
    request.state.audit_action = "update-alert-status"
    request.state.audit_resource_type = "fraud-alert"
    request.state.audit_resource_id = alert_id
    try:
        current_alert = container.alert_service.get_alert(GetAlertQuery(alert_id=alert_id)).alert
        if body.linked_case_id is not None:
            container.case_service.get_case(GetCaseQuery(case_id=body.linked_case_id))
        result = container.alert_service.update_status(
            UpdateAlertStatusCommand(
                alert_id=alert_id,
                status=body.status,
                linked_case_id=body.linked_case_id,
            )
        )
        sync_case_alert_counts(
            container,
            current_alert.linked_case_id,
            result.alert.linked_case_id,
        )
        return result
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/alerts/{alert_id}/case",
    response_model=CreateCaseFromAlertResult,
    tags=["Alerts"],
    summary="Create a case from an alert",
    description=(
        "Creates a persistent fraud case from an alert and links the alert to "
        "that case in a single workflow step."
    ),
)
def create_case_from_alert(
    alert_id: str,
    request: Request,
    container: ContainerDep,
    principal: AnalystDep,
) -> CreateCaseFromAlertResult:
    request.state.current_principal = principal
    request.state.audit_action = "create-case-from-alert"
    request.state.audit_resource_type = "fraud-alert"
    request.state.audit_resource_id = alert_id
    try:
        alert = container.alert_service.get_alert(GetAlertQuery(alert_id=alert_id)).alert
        if alert.linked_case_id:
            raise HTTPException(
                status_code=409,
                detail=f"Alert '{alert_id}' is already linked to case '{alert.linked_case_id}'.",
            )
        if alert.status in {AlertStatus.RESOLVED, AlertStatus.FALSE_POSITIVE}:
            raise HTTPException(
                status_code=409,
                detail=f"Alert '{alert_id}' is already closed and cannot open a case.",
            )

        related_alerts = container.alert_service.list_alerts_for_source(
            source_type=alert.source_type,
            source_id=alert.source_id,
        )
        case_command = build_case_command_from_alert(alert, container)
        validate_case_source(case_command, container)
        created_case, linked_alerts = create_case_with_source_links(
            command=case_command,
            container=container,
            evidence_snapshot=build_case_evidence_snapshot(case_command, container),
            related_alerts=related_alerts,
        )
        updated_alert = next(
            linked_alert
            for linked_alert in linked_alerts
            if linked_alert.alert_id == alert.alert_id
        )
        return CreateCaseFromAlertResult(alert=updated_alert, case=created_case)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

