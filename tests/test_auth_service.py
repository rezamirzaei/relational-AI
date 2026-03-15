from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from relational_fraud_intelligence.application.dto.auth import (
    ListAuditEventsQuery,
    LoginCommand,
)
from relational_fraud_intelligence.application.services.auth_service import (
    AuthenticationError,
    AuthorizationError,
    AuthService,
)
from relational_fraud_intelligence.infrastructure.persistence.models import OperatorUserRecord
from relational_fraud_intelligence.infrastructure.persistence.security_repository import (
    SqlAlchemyAuditLogRepository,
    SqlAlchemyOperatorRepository,
)
from relational_fraud_intelligence.infrastructure.security.passwords import PasswordHasher
from relational_fraud_intelligence.infrastructure.security.tokens import TokenService
from relational_fraud_intelligence.settings import AppSettings


async def test_auth_service_authenticates_and_round_trips_operator(
    operator_repository: SqlAlchemyOperatorRepository,
    audit_repository: SqlAlchemyAuditLogRepository,
) -> None:
    password_hasher = PasswordHasher()
    await operator_repository.create_operator(
        username="reviewer",
        display_name="Case Reviewer",
        role="analyst",
        password_hash=password_hasher.hash_password("ReviewerPassword123!"),
    )
    service = AuthService(
        operator_repository=operator_repository,
        audit_log_repository=audit_repository,
        password_hasher=password_hasher,
        token_service=TokenService(AppSettings()),
        settings=AppSettings(),
    )

    login_result = await service.authenticate(
        LoginCommand(username="reviewer", password="ReviewerPassword123!")
    )
    current_operator = await service.get_current_operator(login_result.access_token)

    assert login_result.principal.username == "reviewer"
    assert current_operator.principal.display_name == "Case Reviewer"


async def test_auth_service_rejects_invalid_password(
    operator_repository: SqlAlchemyOperatorRepository,
    audit_repository: SqlAlchemyAuditLogRepository,
) -> None:
    password_hasher = PasswordHasher()
    await operator_repository.create_operator(
        username="reviewer",
        display_name="Case Reviewer",
        role="analyst",
        password_hash=password_hasher.hash_password("ReviewerPassword123!"),
    )
    service = AuthService(
        operator_repository=operator_repository,
        audit_log_repository=audit_repository,
        password_hasher=password_hasher,
        token_service=TokenService(AppSettings()),
        settings=AppSettings(),
    )

    with pytest.raises(AuthenticationError):
        await service.authenticate(LoginCommand(username="reviewer", password="wrong-password"))


async def test_auth_service_rejects_disabled_operator(
    operator_repository: SqlAlchemyOperatorRepository,
    audit_repository: SqlAlchemyAuditLogRepository,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    password_hasher = PasswordHasher()
    await operator_repository.create_operator(
        username="disabled-user",
        display_name="Disabled User",
        role="analyst",
        password_hash=password_hasher.hash_password("DisabledPassword123!"),
    )
    async with session_factory.begin() as session:
        record = await session.scalar(
            select(OperatorUserRecord).where(OperatorUserRecord.username == "disabled-user")
        )
        assert record is not None
        record.is_active = False

    service = AuthService(
        operator_repository=operator_repository,
        audit_log_repository=audit_repository,
        password_hasher=password_hasher,
        token_service=TokenService(AppSettings()),
        settings=AppSettings(),
    )

    with pytest.raises(AuthorizationError):
        await service.authenticate(
            LoginCommand(username="disabled-user", password="DisabledPassword123!")
        )


async def test_auth_service_rejects_token_for_disabled_operator(
    operator_repository: SqlAlchemyOperatorRepository,
    audit_repository: SqlAlchemyAuditLogRepository,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    password_hasher = PasswordHasher()
    await operator_repository.create_operator(
        username="reviewer",
        display_name="Case Reviewer",
        role="analyst",
        password_hash=password_hasher.hash_password("ReviewerPassword123!"),
    )
    service = AuthService(
        operator_repository=operator_repository,
        audit_log_repository=audit_repository,
        password_hasher=password_hasher,
        token_service=TokenService(AppSettings()),
        settings=AppSettings(),
    )
    login_result = await service.authenticate(
        LoginCommand(username="reviewer", password="ReviewerPassword123!")
    )

    async with session_factory.begin() as session:
        record = await session.scalar(
            select(OperatorUserRecord).where(OperatorUserRecord.username == "reviewer")
        )
        assert record is not None
        record.is_active = False

    with pytest.raises(AuthenticationError):
        await service.get_current_operator(login_result.access_token)


async def test_auth_service_lists_audit_events(
    operator_repository: SqlAlchemyOperatorRepository,
    audit_repository: SqlAlchemyAuditLogRepository,
) -> None:
    service = AuthService(
        operator_repository=operator_repository,
        audit_log_repository=audit_repository,
        password_hasher=PasswordHasher(),
        token_service=TokenService(AppSettings()),
        settings=AppSettings(),
    )
    await audit_repository.record_event(
        request_id="req-123",
        action="list-scenarios",
        resource_type="fraud-scenario",
        http_method="GET",
        path="/api/v1/scenarios",
        status_code=200,
        actor_username="admin",
        actor_role="admin",
        details={"limit": "3"},
    )

    result = await service.list_audit_events(ListAuditEventsQuery(limit=10))

    assert len(result.events) == 1
    assert result.events[0].action == "list-scenarios"
