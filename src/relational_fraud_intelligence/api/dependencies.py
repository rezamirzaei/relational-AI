from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated, cast

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from relational_fraud_intelligence.application.services.auth_service import AuthenticationError
from relational_fraud_intelligence.bootstrap import ApplicationContainer
from relational_fraud_intelligence.domain.models import OperatorPrincipal, OperatorRole

_bearer_scheme = HTTPBearer(auto_error=False)


def get_container(request: Request) -> ApplicationContainer:
    return cast(ApplicationContainer, request.app.state.container)


def get_request_id(request: Request) -> str:
    return cast(str, getattr(request.state, "request_id", "unknown"))


async def get_current_operator(
    request: Request,
    container: Annotated[ApplicationContainer, Depends(get_container)],
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(_bearer_scheme),
    ],
) -> OperatorPrincipal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized("You must authenticate to access this endpoint.")
    try:
        result = await container.auth_service.get_current_operator(credentials.credentials)
    except AuthenticationError as exc:
        raise _unauthorized(str(exc)) from exc

    request.state.current_principal = result.principal
    return result.principal


def require_roles(*allowed_roles: OperatorRole) -> Callable[..., Awaitable[OperatorPrincipal]]:
    async def dependency(
        request: Request,
        principal: Annotated[OperatorPrincipal, Depends(get_current_operator)],
        container: Annotated[ApplicationContainer, Depends(get_container)],
    ) -> OperatorPrincipal:
        if principal.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this endpoint.",
            )

        limit = container.settings.rate_limit_api_requests
        window = container.settings.rate_limit_api_window_seconds
        allowed, retry_after = container.rate_limiter.consume(
            key=f"api:{principal.user_id}",
            limit=limit,
            window_seconds=window,
        )

        # Expose rate-limit info for header propagation by middleware
        request.state.rate_limit_limit = limit
        request.state.rate_limit_remaining = max(0, limit - 1) if allowed else 0
        request.state.rate_limit_reset = retry_after

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="API rate limit exceeded. Please retry shortly.",
                headers={"Retry-After": str(retry_after)},
            )

        request.state.current_principal = principal
        return principal

    return dependency


def enforce_login_rate_limit(
    request: Request,
    username: str,
    container: ApplicationContainer,
) -> None:
    client_ip = request.client.host if request.client is not None else "unknown"
    allowed, retry_after = container.rate_limiter.consume(
        key=f"auth:{client_ip}:{username.strip().lower()}",
        limit=container.settings.rate_limit_auth_requests,
        window_seconds=container.settings.rate_limit_auth_window_seconds,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts. Please retry shortly.",
            headers={"Retry-After": str(retry_after)},
        )


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )
