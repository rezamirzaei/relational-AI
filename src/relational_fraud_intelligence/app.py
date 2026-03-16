import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from relational_fraud_intelligence import __version__
from relational_fraud_intelligence.api.errors import ErrorCode, ErrorResponse
from relational_fraud_intelligence.api.middleware.audit import AuditMiddleware
from relational_fraud_intelligence.api.middleware.request_context import (
    RequestContextMiddleware,
)
from relational_fraud_intelligence.api.middleware.security_headers import (
    SecurityHeadersMiddleware,
)
from relational_fraud_intelligence.api.routes import router
from relational_fraud_intelligence.bootstrap import build_container
from relational_fraud_intelligence.infrastructure.logging import configure_logging
from relational_fraud_intelligence.infrastructure.observability import setup_observability
from relational_fraud_intelligence.settings import AppSettings

_logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: AppSettings = app.state.settings
    configure_logging()
    container = await build_container(settings)
    app.state.container = container
    try:
        yield
    finally:
        # Flush OpenTelemetry spans before shutting down
        otel_provider = getattr(app.state, "otel_tracer_provider", None)
        if otel_provider is not None:
            otel_provider.shutdown()
        await container.shutdown()


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def create_app() -> FastAPI:
    settings = AppSettings()

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description=(
            "A fraud triage workspace for uploaded transaction datasets, with "
            "persistent alerts and cases, plus reference scenario investigations "
            "for validation and rule calibration. Statistical and behavioral "
            "analysis remain the source of truth, while the optional copilot layer explains the "
            "results in operator-facing language."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
        openapi_tags=[
            {"name": "System", "description": "Health and readiness endpoints."},
            {"name": "Authentication", "description": "Operator login and session management."},
            {
                "name": "Investigations",
                "description": "Reference scenario catalog and investigation execution.",
            },
            {
                "name": "Cases",
                "description": "Persistent fraud case workflow for scenarios and datasets.",
            },
            {
                "name": "Alerts",
                "description": "Persistent alert inbox generated from investigations and analyses.",
            },
            {
                "name": "Dashboard",
                "description": "Aggregate metrics, workflow guidance, and recent activity.",
            },
            {
                "name": "Datasets",
                "description": "Upload transaction data and run statistical fraud analysis.",
            },
            {"name": "Admin", "description": "Administrative endpoints for audit and operations."},
        ],
    )

    # ── Global exception handlers (structured error envelope) ──────────

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        body = ErrorResponse(
            error_code=ErrorCode.VALIDATION_ERROR,
            detail=str(exc),
            request_id=_request_id(request),
        )
        return JSONResponse(status_code=422, content=body.model_dump(mode="json"))

    @app.exception_handler(HTTPException)
    async def http_error_handler(
        request: Request,
        exc: HTTPException,
    ) -> JSONResponse:
        code = _STATUS_TO_ERROR_CODE.get(exc.status_code, ErrorCode.INTERNAL_ERROR)
        # Allow routes to override the error_code via exc.detail dict
        detail_text = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        body = ErrorResponse(
            error_code=code,
            detail=detail_text,
            request_id=_request_id(request),
        )
        headers = getattr(exc, "headers", None) or {}
        return JSONResponse(
            status_code=exc.status_code,
            content=body.model_dump(mode="json"),
            headers=headers,
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        _logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        body = ErrorResponse(
            error_code=ErrorCode.INTERNAL_ERROR,
            detail="An unexpected error occurred. Please try again or contact support.",
            request_id=_request_id(request),
        )
        return JSONResponse(status_code=500, content=body.model_dump(mode="json"))

    # Store settings so the lifespan handler uses the same instance
    app.state.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=settings.cors_allowed_methods,
        allow_headers=settings.cors_allowed_headers,
    )
    app.add_middleware(RequestContextMiddleware, request_id_header=settings.request_id_header)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(AuditMiddleware)
    app.include_router(router, prefix=settings.api_prefix)

    # Observability (OpenTelemetry + Prometheus) – opt-in via RFI_OTEL_ENABLED
    setup_observability(app, settings)

    return app


_STATUS_TO_ERROR_CODE: dict[int, ErrorCode] = {
    400: ErrorCode.VALIDATION_ERROR,
    401: ErrorCode.AUTHENTICATION_REQUIRED,
    403: ErrorCode.INSUFFICIENT_PERMISSIONS,
    404: ErrorCode.RESOURCE_NOT_FOUND,
    409: ErrorCode.INVALID_STATUS_TRANSITION,
    413: ErrorCode.VALIDATION_ERROR,
    422: ErrorCode.VALIDATION_ERROR,
    429: ErrorCode.RATE_LIMIT_EXCEEDED,
    500: ErrorCode.INTERNAL_ERROR,
    503: ErrorCode.SERVICE_UNAVAILABLE,
}
