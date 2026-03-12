from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from relational_fraud_intelligence.domain.models import (
    AuditEvent,
    OperatorPrincipal,
    OperatorRole,
)
from relational_fraud_intelligence.infrastructure.persistence.models import (
    AuditEventRecord,
    OperatorUserRecord,
)


class SqlAlchemyOperatorRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def get_operator_by_id(self, user_id: str) -> OperatorPrincipal | None:
        with self._session_factory() as session:
            record = session.get(OperatorUserRecord, user_id)
            if record is None:
                return None
            return _to_principal(record)

    def get_operator_by_username(self, username: str) -> OperatorPrincipal | None:
        normalized_username = username.strip().lower()
        with self._session_factory() as session:
            record = session.scalar(
                select(OperatorUserRecord).where(OperatorUserRecord.username == normalized_username)
            )
            if record is None:
                return None
            return _to_principal(record)

    def get_password_hash(self, username: str) -> str | None:
        normalized_username = username.strip().lower()
        with self._session_factory() as session:
            record = session.scalar(
                select(OperatorUserRecord).where(OperatorUserRecord.username == normalized_username)
            )
            return record.password_hash if record is not None else None

    def update_last_login(self, user_id: str) -> None:
        with self._session_factory.begin() as session:
            record = session.get(OperatorUserRecord, user_id)
            if record is not None:
                record.last_login_at = datetime.now(UTC).replace(tzinfo=None)

    def create_operator(
        self,
        username: str,
        display_name: str,
        role: str,
        password_hash: str,
    ) -> bool:
        normalized_username = username.strip().lower()
        with self._session_factory.begin() as session:
            existing = session.scalar(
                select(OperatorUserRecord).where(OperatorUserRecord.username == normalized_username)
            )
            if existing is not None:
                return False

            session.add(
                OperatorUserRecord(
                    user_id=str(uuid.uuid4()),
                    username=normalized_username,
                    display_name=display_name,
                    role=role,
                    password_hash=password_hash,
                    is_active=True,
                    created_at=datetime.now(UTC).replace(tzinfo=None),
                    last_login_at=None,
                )
            )
        return True


class SqlAlchemyAuditLogRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

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
    ) -> None:
        with self._session_factory.begin() as session:
            session.add(
                AuditEventRecord(
                    occurred_at=datetime.now(UTC).replace(tzinfo=None),
                    request_id=request_id,
                    actor_user_id=actor_user_id,
                    actor_username=actor_username,
                    actor_role=actor_role,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    http_method=http_method,
                    path=path,
                    status_code=status_code,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details=details or {},
                )
            )

    def list_events(self, limit: int) -> list[AuditEvent]:
        with self._session_factory() as session:
            records = session.scalars(
                select(AuditEventRecord).order_by(AuditEventRecord.occurred_at.desc()).limit(limit)
            ).all()
        return [_to_audit_event(record) for record in records]

    def delete_events_older_than(self, cutoff: datetime) -> int:
        with self._session_factory.begin() as session:
            result = session.execute(
                delete(AuditEventRecord).where(AuditEventRecord.occurred_at < cutoff)
            )
        return int(result.rowcount or 0)


def _to_principal(record: OperatorUserRecord) -> OperatorPrincipal:
    return OperatorPrincipal(
        user_id=record.user_id,
        username=record.username,
        display_name=record.display_name,
        role=OperatorRole(record.role),
        is_active=record.is_active,
    )


def _to_audit_event(record: AuditEventRecord) -> AuditEvent:
    return AuditEvent(
        event_id=record.event_id,
        occurred_at=record.occurred_at,
        request_id=record.request_id,
        actor_user_id=record.actor_user_id,
        actor_username=record.actor_username,
        actor_role=OperatorRole(record.actor_role) if record.actor_role is not None else None,
        action=record.action,
        resource_type=record.resource_type,
        resource_id=record.resource_id,
        http_method=record.http_method,
        path=record.path,
        status_code=record.status_code,
        ip_address=record.ip_address,
        user_agent=record.user_agent,
        details=record.details,
    )
