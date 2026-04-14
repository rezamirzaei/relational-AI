from typing import Literal, Self
from urllib.parse import urlparse

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_LOCAL_JWT_SECRET = "local-development-only-jwt-secret-key-0001"


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="RFI_",
        extra="ignore",
    )

    app_name: str = "Relational Fraud Intelligence"
    app_env: str = "local"
    api_prefix: str = "/api/v1"
    api_host: str = "0.0.0.0"
    api_port: int = 8001
    api_docs_enabled: bool | None = None
    cors_allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3001", "http://localhost:3000"]
    )
    cors_allowed_methods: list[str] = Field(
        default_factory=lambda: ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    )
    cors_allowed_headers: list[str] = Field(
        default_factory=lambda: ["Authorization", "Content-Type", "X-Request-ID"]
    )
    database_url: str = "sqlite+pysqlite:///./data/rfi.db"
    database_echo: bool = False
    database_auto_create_schema: bool = True
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_pool_pre_ping: bool = True
    seed_scenarios_on_startup: bool = True
    request_id_header: str = "X-Request-ID"
    max_upload_size_bytes: int = 50 * 1024 * 1024  # 50 MB
    jwt_access_token_ttl_minutes: int = 60
    jwt_algorithm: str = "HS256"
    jwt_secret: str = DEFAULT_LOCAL_JWT_SECRET
    jwt_issuer: str = "relational-fraud-intelligence"
    jwt_audience: str = "rfi-operators"
    bootstrap_admin_username: str | None = None
    bootstrap_admin_password: str | None = None
    bootstrap_admin_display_name: str = "Platform Admin"
    bootstrap_analyst_username: str | None = None
    bootstrap_analyst_password: str | None = None
    bootstrap_analyst_display_name: str = "Fraud Analyst"
    allow_bootstrap_users_in_production: bool = False
    rate_limit_backend: Literal["memory", "redis"] = "memory"
    rate_limit_redis_url: str = "redis://localhost:6379/0"
    rate_limit_auth_requests: int = 10
    rate_limit_auth_window_seconds: int = 60
    rate_limit_api_requests: int = 120
    rate_limit_api_window_seconds: int = 60
    audit_log_retention_days: int = 90

    text_signal_provider: Literal["keyword", "huggingface"] = "keyword"
    reasoning_provider: Literal["local-rule-engine", "relationalai"] = "local-rule-engine"
    explanation_provider: Literal["deterministic", "huggingface"] = "deterministic"

    huggingface_api_token: str | None = None
    huggingface_timeout_seconds: float = 15.0
    huggingface_zero_shot_model: str = "facebook/bart-large-mnli"
    huggingface_explanation_model: str = "HuggingFaceTB/SmolLM2-1.7B-Instruct"
    huggingface_explanation_max_tokens: int = 400

    relationalai_use_external_config: bool = False
    relationalai_duckdb_path: str = ":memory:"

    # Observability (OpenTelemetry + Prometheus) – opt-in
    otel_enabled: bool = False
    otel_service_name: str = "relational-fraud-intelligence"
    otel_exporter_otlp_endpoint: str | None = None

    @property
    def is_production_like(self) -> bool:
        return self.app_env not in {"local", "test", "ci"}

    @property
    def docs_enabled(self) -> bool:
        if self.api_docs_enabled is not None:
            return self.api_docs_enabled
        return not self.is_production_like

    @model_validator(mode="after")
    def validate_security_settings(self) -> Self:
        if len(self.jwt_secret) < 32:
            raise ValueError("RFI_JWT_SECRET must be at least 32 characters long.")

        if self.is_production_like and self.jwt_secret == DEFAULT_LOCAL_JWT_SECRET:
            raise ValueError(
                "RFI_JWT_SECRET must be overridden outside local and test environments."
            )

        if not self.cors_allowed_origins:
            raise ValueError("RFI_CORS_ALLOWED_ORIGINS must include at least one origin.")

        for name, password in {
            "RFI_BOOTSTRAP_ADMIN_PASSWORD": self.bootstrap_admin_password,
            "RFI_BOOTSTRAP_ANALYST_PASSWORD": self.bootstrap_analyst_password,
        }.items():
            if password is not None and len(password) < 12:
                raise ValueError(f"{name} must be at least 12 characters long.")

        if self.is_production_like:
            if self.database_auto_create_schema:
                raise ValueError(
                    "RFI_DATABASE_AUTO_CREATE_SCHEMA must be false outside local "
                    "and test environments."
                )

            if self.rate_limit_backend != "redis":
                raise ValueError(
                    "RFI_RATE_LIMIT_BACKEND must be 'redis' outside local and test environments."
                )

            if self.otel_enabled and not self.otel_exporter_otlp_endpoint:
                raise ValueError(
                    "RFI_OTEL_EXPORTER_OTLP_ENDPOINT is required when "
                    "RFI_OTEL_ENABLED=true outside local and test environments."
                )

            if any(_is_loopback_origin(origin) for origin in self.cors_allowed_origins):
                raise ValueError(
                    "RFI_CORS_ALLOWED_ORIGINS must not use localhost or 127.0.0.1 "
                    "outside local and test environments."
                )

            bootstrap_user_configured = any(
                value
                for value in (
                    self.bootstrap_admin_username,
                    self.bootstrap_admin_password,
                    self.bootstrap_analyst_username,
                    self.bootstrap_analyst_password,
                )
            )
            if bootstrap_user_configured and not self.allow_bootstrap_users_in_production:
                raise ValueError(
                    "Bootstrap operators must not be configured outside local and test "
                    "environments unless RFI_ALLOW_BOOTSTRAP_USERS_IN_PRODUCTION=true."
                )

        return self


def _is_loopback_origin(origin: str) -> bool:
    parsed = urlparse(origin)
    return parsed.hostname in {"localhost", "127.0.0.1"}
