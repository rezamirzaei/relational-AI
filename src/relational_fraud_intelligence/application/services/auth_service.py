from __future__ import annotations

from jwt import InvalidTokenError

from relational_fraud_intelligence.application.dto.auth import (
    GetCurrentOperatorResult,
    ListAuditEventsQuery,
    ListAuditEventsResult,
    LoginCommand,
    LoginResult,
)
from relational_fraud_intelligence.application.ports.security import (
    AuditLogRepository,
    OperatorRepository,
)
from relational_fraud_intelligence.infrastructure.security.passwords import PasswordHasher
from relational_fraud_intelligence.infrastructure.security.tokens import TokenService
from relational_fraud_intelligence.settings import AppSettings


class AuthenticationError(ValueError):
    pass


class AuthorizationError(PermissionError):
    pass


class AuthService:
    def __init__(
        self,
        operator_repository: OperatorRepository,
        audit_log_repository: AuditLogRepository,
        password_hasher: PasswordHasher,
        token_service: TokenService,
        settings: AppSettings,
    ) -> None:
        self._operator_repository = operator_repository
        self._audit_log_repository = audit_log_repository
        self._password_hasher = password_hasher
        self._token_service = token_service
        self._settings = settings

    async def authenticate(self, command: LoginCommand) -> LoginResult:
        principal = await self._operator_repository.get_operator_by_username(command.username)
        password_hash = await self._operator_repository.get_password_hash(command.username)
        if principal is None or password_hash is None:
            raise AuthenticationError("Invalid username or password.")
        if not principal.is_active:
            raise AuthorizationError("This operator account is disabled.")
        if not self._password_hasher.verify_password(command.password, password_hash):
            raise AuthenticationError("Invalid username or password.")

        await self._operator_repository.update_last_login(principal.user_id)
        access_token = self._token_service.issue_access_token(
            user_id=principal.user_id,
            username=principal.username,
            role=principal.role.value,
        )
        return LoginResult(
            access_token=access_token,
            expires_in_seconds=self._settings.jwt_access_token_ttl_minutes * 60,
            principal=principal,
        )

    async def get_current_operator(self, token: str) -> GetCurrentOperatorResult:
        try:
            payload = self._token_service.decode_access_token(token)
        except InvalidTokenError as exc:
            raise AuthenticationError("Your session is invalid or has expired.") from exc

        subject = payload.get("sub")
        if subject is None:
            raise AuthenticationError("Your session is invalid or has expired.")

        principal = await self._operator_repository.get_operator_by_id(subject)
        if principal is None or not principal.is_active:
            raise AuthenticationError("Your session is invalid or has expired.")
        return GetCurrentOperatorResult(principal=principal)

    async def list_audit_events(self, query: ListAuditEventsQuery) -> ListAuditEventsResult:
        return ListAuditEventsResult(
            events=await self._audit_log_repository.list_events(query.limit)
        )
