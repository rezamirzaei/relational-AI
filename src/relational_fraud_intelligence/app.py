from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
from relational_fraud_intelligence.settings import AppSettings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = AppSettings()
    configure_logging()
    container = build_container(settings)
    app.state.container = container
    try:
        yield
    finally:
        container.shutdown()


def create_app() -> FastAPI:
    settings = AppSettings()

    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description=(
            "A production-grade fraud investigation platform with relational case management, "
            "graph-based entity analysis, rule-based risk reasoning, alert management, "
            "operator authentication, audit logging, and rate limiting."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
        openapi_tags=[
            {"name": "System", "description": "Health and readiness endpoints."},
            {"name": "Authentication", "description": "Operator login and session management."},
            {"name": "Investigations", "description": "Scenario catalog and fraud investigation execution."},
            {"name": "Cases", "description": "Fraud case lifecycle management — create, assign, comment, resolve."},
            {"name": "Alerts", "description": "Fraud alert inbox — auto-generated from investigations."},
            {"name": "Dashboard", "description": "Aggregate metrics and activity feed for the analyst overview."},
            {"name": "Datasets", "description": "Upload transaction data and run statistical fraud analysis."},
            {"name": "Admin", "description": "Administrative endpoints for audit and operations."},
        ],
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestContextMiddleware, request_id_header=settings.request_id_header)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(AuditMiddleware)
    app.include_router(router, prefix=settings.api_prefix)
    return app
