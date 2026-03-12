from pathlib import Path

import pytest

from relational_fraud_intelligence.settings import DEFAULT_LOCAL_JWT_SECRET, AppSettings


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
    assert f"http://127.0.0.1:{settings.api_port}/api/v1/health" in compose
    assert f"http://backend:{settings.api_port}/api/v1" in compose
    assert f"http://localhost:{settings.api_port}/api/v1" in ci_workflow
    assert f"API_BASE_URL=http://backend:{settings.api_port}/api/v1" in cd_workflow
