"""Alert aggregate — auto-generated or manually created fraud alerts."""

from __future__ import annotations

from datetime import datetime

from relational_fraud_intelligence.domain.base import AppModel
from relational_fraud_intelligence.domain.enums import (
    AlertStatus,
    RiskLevel,
    WorkflowSourceType,
)


class FraudAlert(AppModel):
    """An auto-generated or manually created alert that may lead to a case.

    Domain invariants:
    - An alert must have severity ≥ MEDIUM to be auto-escalated to a case.
    - Once resolved, an alert cannot be re-opened (terminal state).
    - ``linked_case_id`` may only be set when status is INVESTIGATING or later.
    """

    alert_id: str
    source_type: WorkflowSourceType = WorkflowSourceType.SCENARIO
    source_id: str
    scenario_id: str | None = None
    rule_code: str
    title: str
    severity: RiskLevel
    status: AlertStatus = AlertStatus.NEW
    narrative: str
    assigned_analyst_id: str | None = None
    assigned_analyst_name: str | None = None
    linked_case_id: str | None = None
    created_at: datetime
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None

    def can_escalate(self) -> bool:
        """Return True if this alert is eligible for auto-escalation to a case."""
        return self.severity in (RiskLevel.HIGH, RiskLevel.CRITICAL) and self.status in (
            AlertStatus.NEW,
            AlertStatus.ACKNOWLEDGED,
        )

    @property
    def is_terminal(self) -> bool:
        """Return True if the alert is in a terminal state."""
        return self.status in (AlertStatus.RESOLVED, AlertStatus.FALSE_POSITIVE)


