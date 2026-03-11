from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from relational_fraud_intelligence.api.routes import router
from relational_fraud_intelligence.bootstrap import build_container
from relational_fraud_intelligence.settings import AppSettings


def create_app() -> FastAPI:
    settings = AppSettings()
    container = build_container(settings)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.state.container = container

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router, prefix=settings.api_prefix)
    return app
