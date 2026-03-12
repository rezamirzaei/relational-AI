from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from relational_fraud_intelligence.api.dependencies import (
    enforce_login_rate_limit,
    get_container,
    require_roles,
)
from relational_fraud_intelligence.application.dto.auth import (
    GetCurrentOperatorResult,
    ListAuditEventsQuery,
    ListAuditEventsResult,
    LoginCommand,
    LoginResult,
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
from relational_fraud_intelligence.domain.models import AppModel, OperatorPrincipal, OperatorRole

router = APIRouter()
ContainerDep = Annotated[ApplicationContainer, Depends(get_container)]
AnalystDep = Annotated[
    OperatorPrincipal,
    Depends(require_roles(OperatorRole.ANALYST, OperatorRole.ADMIN)),
]
AdminDep = Annotated[OperatorPrincipal, Depends(require_roles(OperatorRole.ADMIN))]


class HealthResponse(AppModel):
    status: str
    app_name: str
    environment: str
    database_status: str
    rate_limit_status: str
    rate_limit_backend: str
    seeded_scenarios: int
    seeded_operators: int


@router.get("/health", response_model=HealthResponse)
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


@router.post("/auth/token", response_model=LoginResult)
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


@router.get("/auth/me", response_model=GetCurrentOperatorResult)
def get_current_operator(principal: AnalystDep, request: Request) -> GetCurrentOperatorResult:
    request.state.audit_action = "get-current-operator"
    request.state.audit_resource_type = "operator"
    request.state.audit_resource_id = principal.user_id
    return GetCurrentOperatorResult(principal=principal)


@router.get("/audit-events", response_model=ListAuditEventsResult)
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


@router.get("/scenarios", response_model=ListScenariosResult)
def list_scenarios(
    request: Request,
    container: ContainerDep,
    principal: AnalystDep,
) -> ListScenariosResult:
    request.state.current_principal = principal
    request.state.audit_action = "list-scenarios"
    request.state.audit_resource_type = "fraud-scenario"
    return container.scenario_catalog_service.list_scenarios(ListScenariosQuery())


@router.get("/scenarios/{scenario_id}", response_model=GetScenarioResult)
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


@router.post("/investigations", response_model=InvestigateScenarioResult)
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
        return container.investigation_service.execute(command)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
