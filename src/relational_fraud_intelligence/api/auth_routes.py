"""Authentication and audit endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from relational_fraud_intelligence.api._helpers import AdminDep, AnalystDep, ContainerDep
from relational_fraud_intelligence.api.dependencies import enforce_login_rate_limit
from relational_fraud_intelligence.application.dto.auth import (
    GetCurrentOperatorResult,
    ListAuditEventsQuery,
    ListAuditEventsResult,
    LoginCommand,
    LoginResult,
)
from relational_fraud_intelligence.application.services.auth_service import (
    AuthenticationError,
    AuthorizationError,
)

router = APIRouter()


@router.post(
    "/auth/token",
    response_model=LoginResult,
    tags=["Authentication"],
    summary="Authenticate an operator",
    description=(
        "Validates operator credentials and returns a JWT access token for subsequent API calls."
    ),
)
async def login_operator(
    command: LoginCommand,
    request: Request,
    container: ContainerDep,
) -> LoginResult:
    enforce_login_rate_limit(request, command.username, container)
    request.state.audit_action = "authenticate-operator"
    request.state.audit_resource_type = "operator-session"
    request.state.audit_resource_id = command.username.strip().lower()
    try:
        result = await container.auth_service.authenticate(command)
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
async def get_current_operator(principal: AnalystDep, request: Request) -> GetCurrentOperatorResult:
    request.state.audit_action = "get-current-operator"
    request.state.audit_resource_type = "operator"
    request.state.audit_resource_id = principal.user_id
    return GetCurrentOperatorResult(principal=principal)


@router.get(
    "/audit-events",
    response_model=ListAuditEventsResult,
    tags=["Admin"],
    summary="List audit events",
    description="Returns recent audit events. Admin only.",
)
async def list_audit_events(
    query: Annotated[ListAuditEventsQuery, Depends()],
    request: Request,
    container: ContainerDep,
    principal: AdminDep,
) -> ListAuditEventsResult:
    request.state.current_principal = principal
    request.state.audit_action = "list-audit-events"
    request.state.audit_resource_type = "audit-event"
    request.state.audit_details = {"limit": str(query.limit)}
    return await container.auth_service.list_audit_events(query)
