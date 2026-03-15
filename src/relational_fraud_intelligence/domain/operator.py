"""Operator aggregate — operator principals and audit events."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from relational_fraud_intelligence.domain.base import AppModel
from relational_fraud_intelligence.domain.enums import OperatorRole


class OperatorPrincipal(AppModel):
    user_id: str
    username: str
    display_name: str
    role: OperatorRole
    is_active: bool


class AuditEvent(AppModel):
    event_id: int
    occurred_at: datetime
    request_id: str
    actor_user_id: str | None = None
    actor_username: str | None = None
    actor_role: OperatorRole | None = None
    action: str
    resource_type: str
    resource_id: str | None = None
    http_method: str
    path: str
    status_code: int
    ip_address: str | None = None
    user_agent: str | None = None
    details: dict[str, str] = Field(default_factory=dict)

