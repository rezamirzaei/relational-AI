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
