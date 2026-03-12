from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    api_port: int = 8000
    cors_allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    database_url: str = "sqlite+pysqlite:///./data/rfi.db"
    database_echo: bool = False
    database_auto_create_schema: bool = True
    seed_scenarios_on_startup: bool = True

    text_signal_provider: Literal["keyword", "huggingface"] = "keyword"
    reasoning_provider: Literal["local-rule-engine", "relationalai"] = "local-rule-engine"

    huggingface_api_token: str | None = None
    huggingface_timeout_seconds: float = 15.0
    huggingface_zero_shot_model: str = "facebook/bart-large-mnli"

    relationalai_use_external_config: bool = False
    relationalai_duckdb_path: str = ":memory:"
