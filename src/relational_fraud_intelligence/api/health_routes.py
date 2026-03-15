"""Health endpoint."""

from fastapi import APIRouter

from relational_fraud_intelligence.api._helpers import ContainerDep
from relational_fraud_intelligence.application.dto.routes import (
    HealthResponse,
    ProviderPostureResponse,
)

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Check platform health",
    description=(
        "Returns the overall health status of the platform including database, "
        "rate limiter, and seeded data counts."
    ),
)
def health(container: ContainerDep) -> HealthResponse:
    database_ready = container.is_database_ready()
    rate_limiter_ready = container.is_rate_limiter_ready()
    rate_limit_backend_degraded = (
        container.active_rate_limit_backend != container.settings.rate_limit_backend
    )
    provider_fallback_degraded = (
        container.requested_text_signal_provider != container.active_text_signal_provider
        or container.requested_explanation_provider != container.active_explanation_provider
    )
    return HealthResponse(
        status="ok"
        if (
            database_ready
            and rate_limiter_ready
            and not rate_limit_backend_degraded
            and not provider_fallback_degraded
        )
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
        provider_status="degraded" if provider_fallback_degraded else "ready",
        rate_limit_backend=container.active_rate_limit_backend,
        seeded_scenarios=container.seed_result.inserted_scenarios,
        seeded_operators=container.operator_bootstrap_result.created_users,
        provider_posture=ProviderPostureResponse(
            requested_text_signal_provider=container.requested_text_signal_provider,
            active_text_signal_provider=container.active_text_signal_provider,
            requested_reasoning_provider=container.requested_reasoning_provider,
            active_reasoning_provider=container.active_reasoning_provider,
            requested_explanation_provider=container.requested_explanation_provider,
            active_explanation_provider=container.active_explanation_provider,
            notes=container.provider_startup_notes,
        ),
    )

