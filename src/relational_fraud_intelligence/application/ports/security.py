from datetime import datetime
from typing import Protocol

from relational_fraud_intelligence.domain.models import AuditEvent, OperatorPrincipal


class OperatorRepository(Protocol):
    def get_operator_by_id(self, user_id: str) -> OperatorPrincipal | None: ...

    def get_operator_by_username(self, username: str) -> OperatorPrincipal | None: ...

    def get_password_hash(self, username: str) -> str | None: ...

    def update_last_login(self, user_id: str) -> None: ...

    def create_operator(
        self,
        username: str,
        display_name: str,
        role: str,
        password_hash: str,
    ) -> bool: ...


class AuditLogRepository(Protocol):
    def record_event(
        self,
        request_id: str,
        action: str,
        resource_type: str,
        http_method: str,
        path: str,
        status_code: int,
        *,
        actor_user_id: str | None = None,
        actor_username: str | None = None,
        actor_role: str | None = None,
        resource_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        details: dict[str, str] | None = None,
    ) -> None: ...

    def list_events(self, limit: int) -> list[AuditEvent]: ...

    def delete_events_older_than(self, cutoff: datetime) -> int: ...


class RateLimiter(Protocol):
    def consume(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]: ...

    def is_healthy(self) -> bool: ...
