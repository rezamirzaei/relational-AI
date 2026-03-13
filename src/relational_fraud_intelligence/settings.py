from typing import Literal, Self

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
    cors_allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3001", "http://localhost:3000"]
    )
    database_url: str = "sqlite+pysqlite:///./data/rfi.db"
    database_echo: bool = False
    database_auto_create_schema: bool = True
    seed_scenarios_on_startup: bool = True
    request_id_header: str = "X-Request-ID"
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

    @model_validator(mode="after")
    def validate_security_settings(self) -> Self:
        if len(self.jwt_secret) < 32:
            raise ValueError("RFI_JWT_SECRET must be at least 32 characters long.")

        if self.app_env not in {"local", "test"} and self.jwt_secret == DEFAULT_LOCAL_JWT_SECRET:
            raise ValueError(
                "RFI_JWT_SECRET must be overridden outside local and test environments."
            )

        for name, password in {
            "RFI_BOOTSTRAP_ADMIN_PASSWORD": self.bootstrap_admin_password,
            "RFI_BOOTSTRAP_ANALYST_PASSWORD": self.bootstrap_analyst_password,
        }.items():
            if password is not None and len(password) < 12:
                raise ValueError(f"{name} must be at least 12 characters long.")

        return self
