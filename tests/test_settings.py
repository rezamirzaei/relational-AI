from pathlib import Path
from typing import Any

import pytest

from relational_fraud_intelligence.settings import DEFAULT_LOCAL_JWT_SECRET, AppSettings


def _production_settings(**overrides: Any) -> AppSettings:
    values: dict[str, Any] = {
        "app_env": "production",
        "jwt_secret": "production-secret-key-for-tests-0001",
        "database_auto_create_schema": False,
        "rate_limit_backend": "redis",
        "cors_allowed_origins": ["https://console.example.com"],
        "bootstrap_admin_username": None,
        "bootstrap_admin_password": None,
        "bootstrap_analyst_username": None,
        "bootstrap_analyst_password": None,
    }
    values.update(overrides)
    return AppSettings(_env_file=None, **values)


def test_settings_reject_short_jwt_secret() -> None:
    with pytest.raises(ValueError, match="RFI_JWT_SECRET must be at least 32 characters long."):
        AppSettings(_env_file=None, jwt_secret="too-short-secret")


def test_settings_require_secret_override_outside_local_env() -> None:
    with pytest.raises(
        ValueError,
        match="RFI_JWT_SECRET must be overridden outside local and test environments.",
    ):
        AppSettings(_env_file=None, app_env="production", jwt_secret=DEFAULT_LOCAL_JWT_SECRET)


def test_settings_reject_short_bootstrap_password() -> None:
    with pytest.raises(
        ValueError,
        match="RFI_BOOTSTRAP_ADMIN_PASSWORD must be at least 12 characters long.",
    ):
        AppSettings(
            _env_file=None,
            jwt_secret="local-development-jwt-secret-key-change-me-0001",
            bootstrap_admin_password="short-pass",
        )


def test_settings_reject_auto_schema_creation_outside_local_env() -> None:
    with pytest.raises(
        ValueError,
        match="RFI_DATABASE_AUTO_CREATE_SCHEMA must be false outside local and test environments.",
    ):
        _production_settings(database_auto_create_schema=True)


def test_settings_reject_non_redis_rate_limiting_outside_local_env() -> None:
    with pytest.raises(
        ValueError,
        match="RFI_RATE_LIMIT_BACKEND must be 'redis' outside local and test environments.",
    ):
        _production_settings(rate_limit_backend="memory")


def test_settings_reject_bootstrap_users_outside_local_env() -> None:
    with pytest.raises(
        ValueError,
        match="Bootstrap operators must not be configured outside local and test environments",
    ):
        _production_settings(
            bootstrap_admin_username="admin",
            bootstrap_admin_password="AdminPassword123!",
        )


def test_settings_reject_loopback_cors_outside_local_env() -> None:
    with pytest.raises(
        ValueError,
        match="RFI_CORS_ALLOWED_ORIGINS must not use localhost or 127.0.0.1",
    ):
        _production_settings(cors_allowed_origins=["http://localhost:3001"])


def test_settings_require_otlp_endpoint_when_otel_enabled_outside_local_env() -> None:
    with pytest.raises(
        ValueError,
        match="RFI_OTEL_EXPORTER_OTLP_ENDPOINT is required when RFI_OTEL_ENABLED=true",
    ):
        _production_settings(otel_enabled=True)


def test_production_settings_disable_docs_by_default() -> None:
    settings = _production_settings()

    assert settings.docs_enabled is False


def test_default_api_port_matches_documented_runtime_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("RFI_API_PORT", raising=False)
    settings = AppSettings(_env_file=None, jwt_secret=DEFAULT_LOCAL_JWT_SECRET)
    env_template = Path(".env.example").read_text(encoding="utf-8")

    assert settings.api_port == 8001
    assert f"RFI_API_PORT={settings.api_port}" in env_template
    assert f"NEXT_PUBLIC_API_BASE_URL=http://localhost:{settings.api_port}/api/v1" in env_template
    assert f"API_BASE_URL=http://backend:{settings.api_port}/api/v1" in env_template


def test_api_port_matches_container_and_ci_runtime_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("RFI_API_PORT", raising=False)
    settings = AppSettings(_env_file=None, jwt_secret=DEFAULT_LOCAL_JWT_SECRET)
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")
    backend_dockerfile = Path("backend/Dockerfile").read_text(encoding="utf-8")
    frontend_dockerfile = Path("frontend/Dockerfile").read_text(encoding="utf-8")
    ci_workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    cd_workflow = Path(".github/workflows/cd.yml").read_text(encoding="utf-8")

    assert f"EXPOSE {settings.api_port}" in backend_dockerfile
    assert f"ARG API_BASE_URL=http://backend:{settings.api_port}/api/v1" in frontend_dockerfile
    assert (
        f"ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:{settings.api_port}/api/v1"
        in frontend_dockerfile
    )
    assert f'RFI_API_PORT: "{settings.api_port}"' in compose
    assert f"${{RFI_API_HOST_PORT:-{settings.api_port}}}:{settings.api_port}" in compose
    assert f"http://127.0.0.1:{settings.api_port}/api/v1/readyz" in compose
    assert f"http://backend:{settings.api_port}/api/v1" in compose
    assert f"http://localhost:{settings.api_port}/api/v1" in ci_workflow
    assert f"API_BASE_URL=http://backend:{settings.api_port}/api/v1" in cd_workflow
