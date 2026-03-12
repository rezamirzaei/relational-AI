from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File

from relational_fraud_intelligence.api.dependencies import (
    enforce_login_rate_limit,
    get_container,
    require_roles,
)
from relational_fraud_intelligence.application.dto.alerts import (
    ListAlertsQuery,
    ListAlertsResult,
    UpdateAlertStatusCommand,
    UpdateAlertStatusResult,
)
from relational_fraud_intelligence.application.dto.auth import (
    GetCurrentOperatorResult,
    ListAuditEventsQuery,
    ListAuditEventsResult,
    LoginCommand,
    LoginResult,
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
from relational_fraud_intelligence.application.dto.dashboard import (
    GetDashboardStatsQuery,
    GetDashboardStatsResult,
)
from relational_fraud_intelligence.application.dto.investigation import (
    GetScenarioQuery,
    GetScenarioResult,
    InvestigateScenarioCommand,
    InvestigateScenarioResult,
    ListScenariosQuery,
    ListScenariosResult,
)
from relational_fraud_intelligence.application.services.auth_service import (
    AuthenticationError,
    AuthorizationError,
)
from relational_fraud_intelligence.bootstrap import ApplicationContainer
from relational_fraud_intelligence.domain.models import (
    AlertStatus,
    AppModel,
    CaseComment,
    CasePriority,
    CaseStatus,
    OperatorPrincipal,
    OperatorRole,
    RiskLevel,
)

router = APIRouter()
ContainerDep = Annotated[ApplicationContainer, Depends(get_container)]
AnalystDep = Annotated[
    OperatorPrincipal,
    Depends(require_roles(OperatorRole.ANALYST, OperatorRole.ADMIN)),
]
AdminDep = Annotated[OperatorPrincipal, Depends(require_roles(OperatorRole.ADMIN))]


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class HealthResponse(AppModel):
    status: str
    app_name: str
    environment: str
    database_status: str
    rate_limit_status: str
    rate_limit_backend: str
    seeded_scenarios: int
    seeded_operators: int


@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Check platform health",
    description="Returns the overall health status of the platform including database, rate limiter, and seeded data counts.",
)
def health(container: ContainerDep) -> HealthResponse:
    database_ready = container.is_database_ready()
    rate_limiter_ready = container.is_rate_limiter_ready()
    rate_limit_backend_degraded = (
        container.active_rate_limit_backend != container.settings.rate_limit_backend
    )
    return HealthResponse(
        status="ok"
        if database_ready and rate_limiter_ready and not rate_limit_backend_degraded
        else "degraded",
        app_name=container.settings.app_name,
        environment=container.settings.app_env,
        database_status="ready" if database_ready else "unavailable",
        rate_limit_status=(
            "ready"
            if rate_limiter_ready and not rate_limit_backend_degraded
            else "degraded"
            if rate_limiter_ready
            else "unavailable"
        ),
        rate_limit_backend=container.active_rate_limit_backend,
        seeded_scenarios=container.seed_result.inserted_scenarios,
        seeded_operators=container.operator_bootstrap_result.created_users,
    )


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


@router.post(
    "/auth/token",
    response_model=LoginResult,
    tags=["Authentication"],
    summary="Authenticate an operator",
    description="Validates operator credentials and returns a JWT access token for subsequent API calls.",
)
def login_operator(
    command: LoginCommand,
    request: Request,
    container: ContainerDep,
) -> LoginResult:
    enforce_login_rate_limit(request, command.username, container)
    request.state.audit_action = "authenticate-operator"
    request.state.audit_resource_type = "operator-session"
    request.state.audit_resource_id = command.username.strip().lower()
    try:
        result = container.auth_service.authenticate(command)
        request.state.current_principal = result.principal
        return result
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get(
    "/auth/me",
    response_model=GetCurrentOperatorResult,
    tags=["Authentication"],
    summary="Get current operator profile",
)
def get_current_operator(principal: AnalystDep, request: Request) -> GetCurrentOperatorResult:
    request.state.audit_action = "get-current-operator"
    request.state.audit_resource_type = "operator"
    request.state.audit_resource_id = principal.user_id
    return GetCurrentOperatorResult(principal=principal)


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------


@router.get(
    "/audit-events",
    response_model=ListAuditEventsResult,
    tags=["Admin"],
    summary="List audit events",
    description="Returns recent audit events. Admin only.",
)
def list_audit_events(
    query: Annotated[ListAuditEventsQuery, Depends()],
    request: Request,
    container: ContainerDep,
    principal: AdminDep,
) -> ListAuditEventsResult:
    request.state.current_principal = principal
    request.state.audit_action = "list-audit-events"
    request.state.audit_resource_type = "audit-event"
    request.state.audit_details = {"limit": str(query.limit)}
    return container.auth_service.list_audit_events(query)


# ---------------------------------------------------------------------------
# Scenarios & Investigations
# ---------------------------------------------------------------------------


@router.get(
    "/scenarios",
    response_model=ListScenariosResult,
    tags=["Investigations"],
    summary="List fraud scenarios",
    description="Returns all seeded fraud scenarios with baseline risk assessment.",
)
def list_scenarios(
    request: Request,
    container: ContainerDep,
    principal: AnalystDep,
) -> ListScenariosResult:
    request.state.current_principal = principal
    request.state.audit_action = "list-scenarios"
    request.state.audit_resource_type = "fraud-scenario"
    return container.scenario_catalog_service.list_scenarios(ListScenariosQuery())


@router.get(
    "/scenarios/{scenario_id}",
    response_model=GetScenarioResult,
    tags=["Investigations"],
    summary="Get scenario details",
    description="Returns full scenario data including customers, accounts, devices, merchants, and transactions.",
)
def get_scenario(
    scenario_id: str,
    request: Request,
    container: ContainerDep,
    principal: AnalystDep,
) -> GetScenarioResult:
    request.state.current_principal = principal
    request.state.audit_action = "get-scenario"
    request.state.audit_resource_type = "fraud-scenario"
    request.state.audit_resource_id = scenario_id
    try:
        return container.scenario_catalog_service.get_scenario(
            GetScenarioQuery(scenario_id=scenario_id)
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/investigations",
    response_model=InvestigateScenarioResult,
    tags=["Investigations"],
    summary="Run fraud investigation",
    description="Executes a full fraud investigation on a scenario: text signal extraction, rule-based risk reasoning, graph analysis, and case assembly.",
)
def investigate_scenario(
    command: InvestigateScenarioCommand,
    request: Request,
    container: ContainerDep,
    principal: AnalystDep,
) -> InvestigateScenarioResult:
    request.state.current_principal = principal
    request.state.audit_action = "investigate-scenario"
    request.state.audit_resource_type = "fraud-scenario"
    request.state.audit_resource_id = command.scenario_id
    try:
        result = container.investigation_service.execute(command)

        # Auto-generate alerts from high-risk investigations
        if result.investigation.total_risk_score >= 35:
            rule_hits = [
                {
                    "rule_code": hit.rule_code,
                    "title": hit.title,
                    "narrative": hit.narrative,
                }
                for hit in result.investigation.top_rule_hits
            ]
            container.alert_service.generate_alerts_from_investigation(
                scenario_id=command.scenario_id,
                risk_score=result.investigation.total_risk_score,
                rule_hits=rule_hits,
            )

        return result
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------


@router.post(
    "/cases",
    response_model=CreateCaseResult,
    tags=["Cases"],
    summary="Create a fraud case",
    description="Creates a new fraud investigation case, optionally linked to a scenario and assigned to an analyst.",
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
        return container.case_service.create_case(command)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/cases",
    response_model=ListCasesResult,
    tags=["Cases"],
    summary="List fraud cases",
    description="Returns a paginated list of fraud cases with optional status/priority/analyst filters.",
)
def list_cases(
    request: Request,
    container: ContainerDep,
    principal: AnalystDep,
    status: CaseStatus | None = Query(default=None),
    priority: CasePriority | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
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
        return container.case_service.get_case(GetCaseQuery(case_id=case_id))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch(
    "/cases/{case_id}/status",
    response_model=UpdateCaseStatusResult,
    tags=["Cases"],
    summary="Update case status",
    description="Transitions a case through its lifecycle: open → investigating → escalated → resolved → closed.",
)
def update_case_status(
    case_id: str,
    command: UpdateCaseStatusCommand,
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
                status=command.status,
                disposition=command.disposition,
                resolution_notes=command.resolution_notes,
            )
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


class AddCommentBody(AppModel):
    body: str


class AddCommentResult(AppModel):
    comment: CaseComment


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


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------


@router.get(
    "/alerts",
    response_model=ListAlertsResult,
    tags=["Alerts"],
    summary="List fraud alerts",
    description="Returns a paginated list of fraud alerts with optional status/severity filters.",
)
def list_alerts(
    request: Request,
    container: ContainerDep,
    principal: AnalystDep,
    status: AlertStatus | None = Query(default=None),
    severity: RiskLevel | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
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
    command: UpdateAlertStatusCommand,
    request: Request,
    container: ContainerDep,
    principal: AnalystDep,
) -> UpdateAlertStatusResult:
    request.state.current_principal = principal
    request.state.audit_action = "update-alert-status"
    request.state.audit_resource_type = "fraud-alert"
    request.state.audit_resource_id = alert_id
    try:
        return container.alert_service.update_status(
            UpdateAlertStatusCommand(
                alert_id=alert_id,
                status=command.status,
                linked_case_id=command.linked_case_id,
            )
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


@router.get(
    "/dashboard/stats",
    response_model=GetDashboardStatsResult,
    tags=["Dashboard"],
    summary="Get dashboard statistics",
    description="Returns aggregate metrics for the analyst dashboard: case counts, alert counts, risk distribution, and recent activity.",
)
def get_dashboard_stats(
    request: Request,
    container: ContainerDep,
    principal: AnalystDep,
) -> GetDashboardStatsResult:
    request.state.current_principal = principal
    request.state.audit_action = "get-dashboard-stats"
    request.state.audit_resource_type = "dashboard"
    return container.dashboard_service.get_stats(GetDashboardStatsQuery())


# ---------------------------------------------------------------------------
# Datasets & Analysis
# ---------------------------------------------------------------------------


class DatasetResponse(AppModel):
    dataset_id: str
    name: str
    uploaded_at: str
    row_count: int
    status: str
    error_message: str | None = None


class DatasetListResponse(AppModel):
    datasets: list[DatasetResponse]


class AnalysisResultResponse(AppModel):
    analysis: dict[str, object]


class TransactionIngestBody(AppModel):
    name: str = "api-ingestion"
    transactions: list[dict[str, object]]


@router.post(
    "/datasets/upload",
    response_model=DatasetResponse,
    tags=["Datasets"],
    summary="Upload a transaction CSV",
    description=(
        "Upload a CSV file with transaction data for fraud analysis. "
        "Required columns: transaction_id, account_id, amount, timestamp. "
        "Optional: merchant, category, device_fingerprint, ip_country, channel, is_fraud."
    ),
)
async def upload_dataset(
    request: Request,
    container: ContainerDep,
    principal: AnalystDep,
    file: UploadFile = File(...),
) -> DatasetResponse:
    request.state.current_principal = principal
    request.state.audit_action = "upload-dataset"
    request.state.audit_resource_type = "dataset"
    try:
        content = await file.read()
        dataset = container.dataset_service.upload_csv(
            filename=file.filename or "upload.csv",
            content=content,
        )
        request.state.audit_resource_id = dataset.dataset_id
        return DatasetResponse(
            dataset_id=dataset.dataset_id,
            name=dataset.name,
            uploaded_at=dataset.uploaded_at.isoformat(),
            row_count=dataset.row_count,
            status=dataset.status,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/datasets/ingest",
    response_model=DatasetResponse,
    tags=["Datasets"],
    summary="Ingest transactions via API",
    description="Accepts a JSON array of transaction records for programmatic ingestion.",
)
def ingest_transactions(
    body: TransactionIngestBody,
    request: Request,
    container: ContainerDep,
    principal: AnalystDep,
) -> DatasetResponse:
    request.state.current_principal = principal
    request.state.audit_action = "ingest-transactions"
    request.state.audit_resource_type = "dataset"
    try:
        dataset = container.dataset_service.ingest_transactions(
            name=body.name,
            transactions=body.transactions,
        )
        request.state.audit_resource_id = dataset.dataset_id
        return DatasetResponse(
            dataset_id=dataset.dataset_id,
            name=dataset.name,
            uploaded_at=dataset.uploaded_at.isoformat(),
            row_count=dataset.row_count,
            status=dataset.status,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/datasets",
    response_model=DatasetListResponse,
    tags=["Datasets"],
    summary="List uploaded datasets",
)
def list_datasets(
    request: Request,
    container: ContainerDep,
    principal: AnalystDep,
) -> DatasetListResponse:
    request.state.current_principal = principal
    request.state.audit_action = "list-datasets"
    request.state.audit_resource_type = "dataset"
    datasets = container.dataset_service.list_datasets()
    return DatasetListResponse(
        datasets=[
            DatasetResponse(
                dataset_id=d.dataset_id,
                name=d.name,
                uploaded_at=d.uploaded_at.isoformat(),
                row_count=d.row_count,
                status=d.status,
                error_message=d.error_message,
            )
            for d in datasets
        ]
    )


@router.post(
    "/datasets/{dataset_id}/analyze",
    tags=["Datasets"],
    summary="Run fraud analysis on a dataset",
    description=(
        "Executes Benford's Law analysis, statistical outlier detection, "
        "velocity spike detection, and round-amount structuring detection."
    ),
)
def analyze_dataset(
    dataset_id: str,
    request: Request,
    container: ContainerDep,
    principal: AnalystDep,
) -> dict[str, object]:
    request.state.current_principal = principal
    request.state.audit_action = "analyze-dataset"
    request.state.audit_resource_type = "dataset"
    request.state.audit_resource_id = dataset_id
    try:
        result = container.dataset_service.analyze(dataset_id)
        return {"analysis": result.model_dump(mode="json")}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/datasets/{dataset_id}/analysis",
    tags=["Datasets"],
    summary="Get analysis results for a dataset",
)
def get_analysis_results(
    dataset_id: str,
    request: Request,
    container: ContainerDep,
    principal: AnalystDep,
) -> dict[str, object]:
    request.state.current_principal = principal
    request.state.audit_action = "get-analysis-results"
    request.state.audit_resource_type = "dataset"
    request.state.audit_resource_id = dataset_id
    try:
        result = container.dataset_service.get_result(dataset_id)
        return {"analysis": result.model_dump(mode="json")}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


