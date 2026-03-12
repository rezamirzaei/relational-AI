from __future__ import annotations

import logging

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from relational_fraud_intelligence.domain.models import OperatorPrincipal

logger = logging.getLogger("relational_fraud_intelligence.audit")


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        response: Response | None = None
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            container = getattr(request.app.state, "container", None)
            if container is not None:
                principal = getattr(request.state, "current_principal", None)
                if principal is not None and not isinstance(principal, OperatorPrincipal):
                    principal = None

                request_id = getattr(request.state, "request_id", "unknown")
                action = getattr(request.state, "audit_action", _derive_action(request))
                resource_type = getattr(
                    request.state,
                    "audit_resource_type",
                    _derive_resource_type(request),
                )
                resource_id = getattr(request.state, "audit_resource_id", None)
                details = getattr(request.state, "audit_details", {}) or {}
                ip_address = request.client.host if request.client is not None else None
                user_agent = request.headers.get("user-agent")

                container.audit_service.record_http_event(
                    request_id=request_id,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    http_method=request.method,
                    path=request.url.path,
                    status_code=status_code,
                    principal=principal,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details=details,
                )
                logger.info(
                    "request completed",
                    extra={
                        "request_id": request_id,
                        "path": request.url.path,
                        "status_code": status_code,
                        "actor_username": (principal.username if principal is not None else None),
                    },
                )


def _derive_action(request: Request) -> str:
    path = request.url.path
    if path.endswith("/auth/token"):
        return "authenticate-operator"
    if path.endswith("/auth/me"):
        return "get-current-operator"
    if path.endswith("/audit-events"):
        return "list-audit-events"
    if path.endswith("/investigations"):
        return "investigate-scenario"
    if path.endswith("/scenarios"):
        return "list-scenarios"
    if "/scenarios/" in path:
        return "get-scenario"
    if path.endswith("/health"):
        return "health-check"
    return "http-request"


def _derive_resource_type(request: Request) -> str:
    path = request.url.path
    if path.endswith("/auth/token") or path.endswith("/auth/me"):
        return "operator-session"
    if path.endswith("/audit-events"):
        return "audit-event"
    if path.endswith("/investigations") or "/scenarios" in path:
        return "fraud-scenario"
    if path.endswith("/health"):
        return "system"
    return "application"
