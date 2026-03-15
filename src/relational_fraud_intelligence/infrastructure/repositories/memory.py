"""In-memory repositories for cases and alerts.

These implementations store data in process memory, which is appropriate for
local development and testing. In production, these would be backed by
SQLAlchemy repositories with Postgres persistence.
"""

from __future__ import annotations

from relational_fraud_intelligence.domain.models import (
    AlertStatus,
    CaseComment,
    CasePriority,
    CaseStatus,
    FraudAlert,
    FraudCase,
    RiskLevel,
    WorkflowSourceType,
)


class InMemoryCaseRepository:
    def __init__(self) -> None:
        self._cases: dict[str, FraudCase] = {}
        self._comments: dict[str, list[CaseComment]] = {}

    async def create_case(self, case: FraudCase) -> None:
        self._cases[case.case_id] = case
        self._comments.setdefault(case.case_id, [])

    async def get_case(self, case_id: str) -> FraudCase | None:
        return self._cases.get(case_id)

    async def update_case(self, case: FraudCase) -> None:
        self._cases[case.case_id] = case

    async def list_cases(
        self,
        *,
        status: CaseStatus | None = None,
        priority: CasePriority | None = None,
        assigned_analyst_id: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[FraudCase], int]:
        filtered = list(self._cases.values())
        if status is not None:
            filtered = [c for c in filtered if c.status == status]
        if priority is not None:
            filtered = [c for c in filtered if c.priority == priority]
        if assigned_analyst_id is not None:
            filtered = [c for c in filtered if c.assigned_analyst_id == assigned_analyst_id]
        filtered.sort(key=lambda c: c.updated_at, reverse=True)
        total = len(filtered)
        start = (page - 1) * page_size
        return filtered[start : start + page_size], total

    async def add_comment(self, comment: CaseComment) -> None:
        self._comments.setdefault(comment.case_id, []).append(comment)

    async def list_comments(self, case_id: str) -> list[CaseComment]:
        return sorted(
            self._comments.get(case_id, []),
            key=lambda c: c.created_at,
            reverse=True,
        )

    async def count_by_status(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for case in self._cases.values():
            counts[case.status] = counts.get(case.status, 0) + 1
        return counts

    async def count_critical(self) -> int:
        return sum(
            1
            for case in self._cases.values()
            if case.priority == CasePriority.CRITICAL
            and case.status not in {CaseStatus.RESOLVED, CaseStatus.CLOSED}
        )


class InMemoryAlertRepository:
    def __init__(self) -> None:
        self._alerts: dict[str, FraudAlert] = {}

    async def create_alert(self, alert: FraudAlert) -> None:
        self._alerts[alert.alert_id] = alert

    async def get_alert(self, alert_id: str) -> FraudAlert | None:
        return self._alerts.get(alert_id)

    async def update_alert(self, alert: FraudAlert) -> None:
        self._alerts[alert.alert_id] = alert

    async def list_alerts(
        self,
        *,
        status: AlertStatus | None = None,
        severity: RiskLevel | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[FraudAlert], int]:
        filtered = list(self._alerts.values())
        if status is not None:
            filtered = [a for a in filtered if a.status == status]
        if severity is not None:
            filtered = [a for a in filtered if a.severity == severity]
        filtered.sort(key=lambda a: a.created_at, reverse=True)
        total = len(filtered)
        start = (page - 1) * page_size
        return filtered[start : start + page_size], total

    async def count_unacknowledged(self) -> int:
        return sum(1 for a in self._alerts.values() if a.status == AlertStatus.NEW)

    async def count_by_severity(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for alert in self._alerts.values():
            counts[alert.severity] = counts.get(alert.severity, 0) + 1
        return counts

    async def list_alerts_for_source(
        self,
        *,
        source_type: WorkflowSourceType,
        source_id: str,
    ) -> list[FraudAlert]:
        return [
            alert
            for alert in self._alerts.values()
            if alert.source_type == source_type and alert.source_id == source_id
        ]

    async def count_linked_to_case(self, case_id: str) -> int:
        return sum(1 for alert in self._alerts.values() if alert.linked_case_id == case_id)
