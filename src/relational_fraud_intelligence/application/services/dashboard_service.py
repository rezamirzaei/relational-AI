from __future__ import annotations

from datetime import datetime, timezone

from relational_fraud_intelligence.application.dto.dashboard import (
    GetDashboardStatsQuery,
    GetDashboardStatsResult,
)
from relational_fraud_intelligence.application.dto.investigation import ListScenariosQuery
from relational_fraud_intelligence.application.ports.repositories import ScenarioRepository
from relational_fraud_intelligence.application.services.alert_service import AlertRepository
from relational_fraud_intelligence.application.services.case_service import CaseRepository
from relational_fraud_intelligence.domain.models import (
    ActivityEvent,
    DashboardStats,
)


class DashboardService:
    def __init__(
        self,
        scenario_repository: ScenarioRepository,
        case_repository: CaseRepository,
        alert_repository: AlertRepository,
    ) -> None:
        self._scenario_repo = scenario_repository
        self._case_repo = case_repository
        self._alert_repo = alert_repository

    def get_stats(self, query: GetDashboardStatsQuery) -> GetDashboardStatsResult:
        _ = query
        scenarios = self._scenario_repo.list_scenarios(ListScenariosQuery())
        cases_by_status = self._case_repo.count_by_status()
        critical_cases = self._case_repo.count_critical()
        alerts_by_severity = self._alert_repo.count_by_severity()
        unacknowledged = self._alert_repo.count_unacknowledged()

        total_cases = sum(cases_by_status.values())
        open_cases = cases_by_status.get("open", 0) + cases_by_status.get("investigating", 0)
        total_alerts = sum(alerts_by_severity.values())

        # Compute risk distribution from scenarios
        risk_distribution: dict[str, int] = {}
        for scenario in scenarios.scenarios:
            level = scenario.baseline_risk
            risk_distribution[level] = risk_distribution.get(level, 0) + 1

        avg_risk = 0.0
        if scenarios.scenarios:
            risk_map = {"low": 15, "medium": 45, "high": 70, "critical": 90}
            avg_risk = sum(
                risk_map.get(s.baseline_risk, 50) for s in scenarios.scenarios
            ) / len(scenarios.scenarios)

        # Build recent activity from cases and alerts
        activity: list[ActivityEvent] = []
        if total_cases > 0:
            activity.append(
                ActivityEvent(
                    event_type="case-update",
                    description=f"{total_cases} cases tracked, {open_cases} currently active",
                    occurred_at=datetime.now(timezone.utc),
                )
            )
        if total_alerts > 0:
            activity.append(
                ActivityEvent(
                    event_type="alert-generated",
                    description=f"{total_alerts} alerts generated, {unacknowledged} awaiting review",
                    occurred_at=datetime.now(timezone.utc),
                )
            )

        return GetDashboardStatsResult(
            stats=DashboardStats(
                total_scenarios=len(scenarios.scenarios),
                total_cases=total_cases,
                open_cases=open_cases,
                critical_cases=critical_cases,
                total_alerts=total_alerts,
                unacknowledged_alerts=unacknowledged,
                avg_risk_score=round(avg_risk, 1),
                cases_by_status=cases_by_status,
                alerts_by_severity=alerts_by_severity,
                recent_activity=activity,
                risk_distribution=risk_distribution,
            )
        )

