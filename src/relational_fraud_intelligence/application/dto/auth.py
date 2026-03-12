from pydantic import Field

from relational_fraud_intelligence.domain.models import AppModel, AuditEvent, OperatorPrincipal


class LoginCommand(AppModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=256)


class LoginResult(AppModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
    principal: OperatorPrincipal


class GetCurrentOperatorResult(AppModel):
    principal: OperatorPrincipal


class ListAuditEventsQuery(AppModel):
    limit: int = Field(default=50, ge=1, le=200)


class ListAuditEventsResult(AppModel):
    events: list[AuditEvent]
