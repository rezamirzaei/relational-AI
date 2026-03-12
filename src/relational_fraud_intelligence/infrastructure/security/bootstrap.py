from __future__ import annotations

from dataclasses import dataclass

from relational_fraud_intelligence.application.ports.security import OperatorRepository
from relational_fraud_intelligence.infrastructure.security.passwords import PasswordHasher
from relational_fraud_intelligence.settings import AppSettings


@dataclass(slots=True)
class OperatorBootstrapResult:
    created_users: int


class OperatorBootstrapper:
    def __init__(
        self,
        repository: OperatorRepository,
        password_hasher: PasswordHasher,
        settings: AppSettings,
    ) -> None:
        self._repository = repository
        self._password_hasher = password_hasher
        self._settings = settings

    def bootstrap(self) -> OperatorBootstrapResult:
        created_users = 0
        created_users += self._create_user_if_configured(
            username=self._settings.bootstrap_admin_username,
            password=self._settings.bootstrap_admin_password,
            display_name=self._settings.bootstrap_admin_display_name,
            role="admin",
        )
        created_users += self._create_user_if_configured(
            username=self._settings.bootstrap_analyst_username,
            password=self._settings.bootstrap_analyst_password,
            display_name=self._settings.bootstrap_analyst_display_name,
            role="analyst",
        )
        return OperatorBootstrapResult(created_users=created_users)

    def _create_user_if_configured(
        self,
        *,
        username: str | None,
        password: str | None,
        display_name: str,
        role: str,
    ) -> int:
        if not username or not password:
            return 0
        password_hash = self._password_hasher.hash_password(password)
        created = self._repository.create_operator(
            username=username,
            display_name=display_name,
            role=role,
            password_hash=password_hash,
        )
        return 1 if created else 0
