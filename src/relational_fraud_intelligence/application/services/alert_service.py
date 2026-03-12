from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol
from uuid import uuid4

from relational_fraud_intelligence.application.dto.alerts import (
    CreateAlertCommand,
    CreateAlertResult,
    GetAlertQuery,
    GetAlertResult,
    ListAlertsQuery,
    ListAlertsResult,
    UpdateAlertStatusCommand,
    UpdateAlertStatusResult,
)
from relational_fraud_intelligence.domain.models import (
    AlertStatus,
    FraudAlert,
    RiskLevel,
)


class AlertRepository(Protocol):
    def create_alert(self, alert: FraudAlert) -> None: ...
    def get_alert(self, alert_id: str) -> FraudAlert | None: ...
    def update_alert(self, alert: FraudAlert) -> None: ...
    def list_alerts(
        self,
        *,
        status: AlertStatus | None = None,
        severity: RiskLevel | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[FraudAlert], int]: ...
    def count_unacknowledged(self) -> int: ...
    def count_by_severity(self) -> dict[str, int]: ...


class AlertService:
    def __init__(self, alert_repository: AlertRepository) -> None:
        self._repo = alert_repository

    def create_alert(self, command: CreateAlertCommand) -> CreateAlertResult:
        now = datetime.now(timezone.utc)
        alert = FraudAlert(
            alert_id=str(uuid4()),
            scenario_id=command.scenario_id,
            rule_code=command.rule_code,
            title=command.title,
            severity=command.severity,
            status=AlertStatus.NEW,
            narrative=command.narrative,
            created_at=now,
        )
        self._repo.create_alert(alert)
        return CreateAlertResult(alert=alert)

    def update_status(self, command: UpdateAlertStatusCommand) -> UpdateAlertStatusResult:
        alert = self._repo.get_alert(command.alert_id)
        if alert is None:
            raise LookupError(f"Alert '{command.alert_id}' not found.")

        now = datetime.now(timezone.utc)
        alert.status = command.status
        if command.linked_case_id is not None:
            alert.linked_case_id = command.linked_case_id
        if command.status == AlertStatus.ACKNOWLEDGED:
            alert.acknowledged_at = now
        if command.status in {AlertStatus.RESOLVED, AlertStatus.FALSE_POSITIVE}:
            alert.resolved_at = now

        self._repo.update_alert(alert)
        return UpdateAlertStatusResult(alert=alert)

    def get_alert(self, query: GetAlertQuery) -> GetAlertResult:
        alert = self._repo.get_alert(query.alert_id)
        if alert is None:
            raise LookupError(f"Alert '{query.alert_id}' not found.")
        return GetAlertResult(alert=alert)

    def list_alerts(self, query: ListAlertsQuery) -> ListAlertsResult:
        alerts, total = self._repo.list_alerts(
            status=query.status,
            severity=query.severity,
            page=query.page,
            page_size=query.page_size,
        )
        return ListAlertsResult(
            alerts=alerts,
            total_count=total,
            page=query.page,
            page_size=query.page_size,
        )

    def generate_alerts_from_investigation(
        self,
        scenario_id: str,
        risk_score: int,
        rule_hits: list[dict[str, object]],
    ) -> list[FraudAlert]:
        """Auto-generate alerts when risk score crosses thresholds."""
        generated: list[FraudAlert] = []
        if risk_score < 35:
            return generated

        from relational_fraud_intelligence.domain.models import RiskLevel

        severity = RiskLevel.MEDIUM
        if risk_score >= 80:
            severity = RiskLevel.CRITICAL
        elif risk_score >= 60:
            severity = RiskLevel.HIGH

        for hit in rule_hits[:3]:
            result = self.create_alert(
                CreateAlertCommand(
                    scenario_id=scenario_id,
                    rule_code=str(hit.get("rule_code", "unknown")),
                    title=str(hit.get("title", "Fraud alert")),
                    severity=severity,
                    narrative=str(hit.get("narrative", "Auto-generated from investigation.")),
                )
            )
            generated.append(result.alert)

        return generated

