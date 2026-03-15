from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from relational_fraud_intelligence.application.services.audit_service import AuditService
from relational_fraud_intelligence.infrastructure.persistence.models import AuditEventRecord
from relational_fraud_intelligence.infrastructure.persistence.security_repository import (
    SqlAlchemyAuditLogRepository,
)


async def test_audit_service_prunes_expired_events(
    audit_repository: SqlAlchemyAuditLogRepository,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    async with session_factory.begin() as session:
        session.add_all(
            [
                AuditEventRecord(
                    occurred_at=now - timedelta(days=120),
                    request_id="old-request",
                    actor_user_id=None,
                    actor_username=None,
                    actor_role=None,
                    action="health-check",
                    resource_type="system",
                    resource_id=None,
                    http_method="GET",
                    path="/api/v1/health",
                    status_code=200,
                    ip_address=None,
                    user_agent=None,
                    details={},
                ),
                AuditEventRecord(
                    occurred_at=now - timedelta(days=10),
                    request_id="fresh-request",
                    actor_user_id=None,
                    actor_username=None,
                    actor_role=None,
                    action="list-scenarios",
                    resource_type="fraud-scenario",
                    resource_id=None,
                    http_method="GET",
                    path="/api/v1/scenarios",
                    status_code=200,
                    ip_address=None,
                    user_agent=None,
                    details={},
                ),
            ]
        )

    service = AuditService(audit_repository)
    pruned_events = await service.prune_expired_events(90)
    remaining_events = await audit_repository.list_events(limit=10)

    assert pruned_events == 1
    assert len(remaining_events) == 1
    assert remaining_events[0].request_id == "fresh-request"
