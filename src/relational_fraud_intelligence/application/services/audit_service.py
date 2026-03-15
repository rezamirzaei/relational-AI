from __future__ import annotations

from datetime import UTC, datetime, timedelta

from relational_fraud_intelligence.application.ports.security import AuditLogRepository
from relational_fraud_intelligence.domain.models import OperatorPrincipal


class AuditService:
    def __init__(self, repository: AuditLogRepository) -> None:
        self._repository = repository

    async def record_http_event(
        self,
        *,
        request_id: str,
        action: str,
        resource_type: str,
        http_method: str,
        path: str,
        status_code: int,
        principal: OperatorPrincipal | None = None,
        resource_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        details: dict[str, str] | None = None,
    ) -> None:
        await self._repository.record_event(
            request_id=request_id,
            actor_user_id=principal.user_id if principal is not None else None,
            actor_username=principal.username if principal is not None else None,
            actor_role=principal.role.value if principal is not None else None,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            http_method=http_method,
            path=path,
            status_code=status_code,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
        )

    async def prune_expired_events(self, retention_days: int) -> int:
        cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=retention_days)
        return await self._repository.delete_events_older_than(cutoff)
